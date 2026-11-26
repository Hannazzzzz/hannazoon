# hannazoon.com

```
 . . . . . . . . . . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . . . . . . . . . .
 . .HA// NN//. . A// . .ZO// ON//.HA// NN//. . A// . . .
. . ZO//.ON// . HAN// . NAZ//OO// NHA//NN// . AZO// . .
 . .ONHANNA//. .ZOO//. .NHAN/NA//.ZOON/HA//. .NNA//. . .
. . ZO///ON// .HA/NN//. AZ/OONH// AN/NAZO// .ON/HA//. .
 . .NN// AZ//.OONHANN//.AZ//OON//.HA//NNA//.ZOONHAN//. .
. . NA//.ZO//ON/////HA//NN//.AZ// OO//.NH//AN/////NA//.
 . . /// .///.///. . /// /// .///. /// .///.///. . /// .
. . . . . . . . . . . . . . . . . . . . . . . . . . . .
 . . . .ZOONHA// .NNAZOO// . .NHANNA// .ZO// ON//. . . .
. . . . .///HA//.NN////AZ// .OO////NH// ANN//AZ// . . .
 . . . . . OO///NH///. .AN//NA///. .ZO//ONHA/NN//. . . .
. . . . . AZ/// OO//. . NH//AN//. . NA//ZO/ONHA// . . .
 . . . . NN/// . AZ//. OO/// NH//. AN///NA//ZOO//. . . .
. . . . NHANNA//. ZOONHA/// . NNAZOO/// NH//.AN// . . .
 . . . . /////// . /////// . . /////// . /// .///. . . .
. . . . . . . . . . . . . . . . . . . . . . . . . . . .
 . . . . . . . . . . . . . . . . . . . . . . . . . . . .
```

Hanna Zoon's homepage: one screen filled with characters, her name drawn as a mosaic in Futura-style capitals, and her links woven into the same grid of text.

Live at **https://hannazoon.com**.

## Why it isn't just an HTML file

It could have been one hand-written `index.html`. It's two small files instead, on purpose.

**The content is Gemtext.** Everything the page says lives in [`site.gmi`](site.gmi), about a dozen lines in Gemtext, the markup of the [Gemini protocol](https://geminiprotocol.net/) (2019): a small, text-first alternative to the web, and nothing to do with Google's AI of the same name. Gemtext has one rule per line, and a link is literally `=> URL label`, so the file already reads like a list of links. It is also the whole editing interface: Hanna tells Claude what the site should say, Claude changes a line of Gemtext, and nothing else can break.

**The letters can't be typed, they have to be computed.** [`build.py`](build.py) draws every capital from geometric shapes (rectangles, circles and parallelograms) and checks, character by character, whether that cell's centre falls inside a letter. Stroke widths are snapped to whole characters: stems are 3 characters wide, bars 2 rows tall, and every diagonal exactly 3 characters on every row. So every corner is square, every O is symmetrical and repeated letters are identical. The letters are then filled with `HANNAZOON` on repeat, with a `/` drop shadow on a dotted background.

**It fits any screen without JavaScript.** The build writes four versions of the mosaic (tall phone, portrait, landscape and ultrawide), and plain CSS shows the one that matches the screen's shape.

**Keeping content and design apart keeps accessibility safe.** The design, the font and all the accessibility work live in `build.py`; the words live in `site.gmi`. Updating a link can't remove a focus outline or put the decoration back in front of a screen reader.

`build.py` is about 500 lines of Python using only the standard library: no packages, no framework and nothing in the page that calls out to another site.

## Accessibility

- Every decorative character is `aria-hidden`. Screen readers hear one heading, "Hanna Zoon", and then the links.
- The links are real `<a>` elements sitting in the grid, in classic blue, turning purple once visited, with a visible focus outline.
- No sideways scrolling, a minimum text size, and support for Windows high-contrast mode.
- Nothing moves, so there's nothing to switch off for people who prefer reduced motion.

## How to update the site

All content changes happen in `site.gmi`. After every commit to `main`, the [deploy workflow](.github/workflows/deploy.yml) runs `python3 build.py` and publishes the new page, usually within a minute or two.

### On github.com (easiest, works from a phone)

1. Open [`site.gmi`](site.gmi) and click the pencil icon.
2. Make the change (examples below).
3. Click **Commit changes**, and commit straight to `main`.
4. Wait a minute, then reload https://hannazoon.com. If nothing changed, check the **Actions** tab: a red cross means the build failed, and the log says why.

### With Claude

Tell Claude what the site should say ("add my Mastodon", "rename Blog to Writing"). Claude updates `site.gmi`, checks the result, and either commits it on github.com in the browser (with your permission) or gives you the new file to paste in.

### On your computer, with git

```
git clone https://github.com/Hannazzzzz/hannazoon.git
cd hannazoon
# edit site.gmi
python3 build.py          # writes index.html; open it in a browser to check
git commit -am "Update links"
git push
```

### Common changes

- **Add a link:** add a line `=> https://example.com Label`. Links appear in the order listed.
- **Rename a link:** change the text after the address.
- **Remove a link:** delete its line.
- **Change the name in the mosaic:** change the first `# ` line. Letters A to Z use the Futura-style capitals; numbers and punctuation fall back to a simple pixel font.
- **Change the mosaic's characters:** edit the ` ```mosaic ` block, for example `fill: HELLO` or `texture: "/ "`.
- **Change the design, the font or the colours:** that's in `build.py`, not `site.gmi`.

### Gemtext cheat sheet

```
# Hanna Zoon          the first heading becomes the mosaic
=> https://... Label  a link (links sit side by side and wrap)
Plain text            a paragraph
## Heading            a section heading
* Item                a bullet
```

A ` ```mosaic ` block sets the characters: `fill` (the letters, used in turn), `shadow` and `texture` (the background pattern).

## Files

- `site.gmi`: the content
- `build.py`: turns it into `index.html` (generated, so not kept in the repository)
- `.github/workflows/deploy.yml`: builds and publishes on every push

Made by Hanna Zoon with Claude.
