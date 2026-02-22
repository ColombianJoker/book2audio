# book2audio
Book2Audio: Python utility to create audio files from books in `.epub` format

## Uses:

  + `ebooklib` to process the `.epub` files
  + `beautifulsoup4` to parse the text inside the books

  ---

## Syntax:

```
usage: book2audio.py
    [ -a AUTHOR ] -- The author to use (when not detected in the book)
    [ -t TITLE ]  -- The title to use (when not detected in the book)
    [ -f {.m4a,.mp3,.wav,.aiff,m4a,mp3,wav,aiff} ] -- Audio file format
    [ -F FILENAME_FORMAT ] -- Name generation format
    [ -v ]        -- Verbose mode
    file [files ...]
```
