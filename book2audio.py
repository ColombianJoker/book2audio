#!/usr/bin/env python3.11
#
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

from bs4 import BeautifulSoup
from ebooklib import epub


def log(message, verbose):
    """Prints a message if verbose mode is enabled."""
    if verbose:
        print(f"[INFO] {message}")


def get_epub_metadata(book):
    """Extracts author and title from EPUB metadata."""
    title = ""
    author = ""

    # Get Title
    titles = book.get_metadata("DC", "title")
    if titles:
        title = titles[0][0]

    # Get Author
    creators = book.get_metadata("DC", "creator")
    if creators:
        author = creators[0][0]

    return author, title


def clean_html(content):
    """Extracts clean text from HTML/XHTML content."""
    soup = BeautifulSoup(content, "html.parser")
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.extract()
    return soup.get_text(separator=" ")


def convert_audio(input_file, output_file, ext, verbose):
    """Converts AIFF to the target format using ffmpeg."""
    log(f"Converting {input_file} to {output_file} ({ext})", verbose)

    cmd = ["ffmpeg", "-y", "-i", input_file]

    if ext == ".mp3":
        # Optimized for voice: Mono, 64k (standard for speech), variable bitrate
        cmd += ["-ac", "1", "-libmp3lame", "-q:a", "5"]
    elif ext == ".m4a":
        cmd += ["-c:a", "aac", "-b:a", "128k"]
    elif ext == ".wav":
        cmd += ["-ar", "44100"]
    elif ext == ".aiff":
        # say already produces aiff, just a copy/rename if needed
        shutil.move(input_file, output_file)
        return

    cmd.append(output_file)

    try:
        subprocess.run(
            cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        print(
            f"[ERROR] Failed to convert to {ext}. Is ffmpeg installed?", file=sys.stderr
        )
    except FileNotFoundError:
        print(
            "[ERROR] ffmpeg not found. Please install it (brew install ffmpeg) for conversions.",
            file=sys.stderr,
        )


def process_book(filepath, args):
    """Main processing logic for a single EPUB file."""
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return

    try:
        book = epub.read_epub(filepath)
    except Exception as e:
        print(f"[ERROR] Could not read EPUB {filepath}: {e}")
        return

    # Metadata Identification
    meta_author, meta_title = get_epub_metadata(book)

    author = (
        args.author
        if args.author
        else (meta_author if meta_author else "Unknown Author")
    )
    title = (
        args.title if args.title else (meta_title if meta_title else "Unknown Title")
    )

    log(f"Identified Author: {author}", args.verbose)
    log(f"Identified Title: {title}", args.verbose)

    # Clean up names for filesystem
    safe_author = re.sub(r'[\\/*?:"<>|]', "", author)
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)

    # Iterate through chapters
    chapter_num = 1
    for item in book.get_items():
        if item.get_type() == 9:  # ITEM_DOCUMENT
            content = item.get_content()
            text = clean_html(content).strip()

            # Skip empty chapters
            if len(text) < 100:
                continue

            log(f"Processing Chapter {chapter_num}...", args.verbose)

            # Format filename
            ext = args.format if args.format.startswith(".") else f".{args.format}"
            filename_template = args.filename_format.replace(
                "${Author}", safe_author
            ).replace("${Title}", safe_title)
            final_filename = filename_template % chapter_num
            # Handle the extension replacement manually or ensure it's in the template
            if "${ext}" in final_filename:
                final_filename = final_filename.replace("${ext}", ext.strip("."))
            else:
                final_filename += ext

            # TTS Generation
            temp_aiff = tempfile.NamedTemporaryFile(suffix=".aiff", delete=False).name
            try:
                # Use macOS native 'say' command
                subprocess.run(["say", "-o", temp_aiff, text], check=True)

                # Convert to target format
                convert_audio(temp_aiff, final_filename, ext, args.verbose)

                if os.path.exists(temp_aiff):
                    os.remove(temp_aiff)

            except Exception as e:
                print(
                    f"[ERROR] TTS or Conversion failed for chapter {chapter_num}: {e}"
                )

            chapter_num += 1


def main():
    parser = argparse.ArgumentParser(
        description="Convert EPUB books to audiobooks natively on macOS."
    )

    parser.add_argument("files", nargs="+", help="One or more .epub files to process")
    parser.add_argument("-a", "--author", help="Override the author name")
    parser.add_argument("-t", "--title", help="Override the book title")
    parser.add_argument(
        "-f",
        "--format",
        default=".m4a",
        choices=[".m4a", ".mp3", ".wav", ".aiff", "m4a", "mp3", "wav", "aiff"],
        help="Audio format (default: .m4a)",
    )
    parser.add_argument(
        "-F",
        "--filename-format",
        default="${Author}-${Title} - Chapter %02d.${ext}",
        help="Output filename format. Use ${Author}, ${Title}, and ${ext}",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show progress details"
    )

    args = parser.parse_args()

    # Ensure format starts with dot
    if not args.format.startswith("."):
        args.format = f".{args.format}"

    for epub_file in args.files:
        log(f"Starting processing for: {epub_file}", args.verbose)
        process_book(epub_file, args)


if __name__ == "__main__":
    main()
