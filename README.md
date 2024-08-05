## Intro
This is a small collection of utilities that I created years ago to help manipulate binary images for the Run-DMD clock (https://run-dmd.com/).  The utilities allow for animations to be ripped, modified, and (re)combined.  There are also a few ancillary scripts for adding custom animations from other things like animated GIFs, video files, or raw files captured from the WPC emulator (https://playfield.dev/)

## Utilities
Here is a short overview of the purpose and usage of each item in the repository
- `rip_image.py`: This Python script is used to extract the header and all of the animations from a Run-DMD binary image to a set of JSON files
-- **Example:** `rip_image.py --image RunDMD_B134.img --output-dir b134_extracted`

- `raw_to_json.py`: This Python script is used to create a single JSON animation file using a RAW file created from https://playfield.dev/
-- **Example:** `raw_to_json.py --input-raw party_zone_dmd.raw --output-json b134_extracted/PARTY_ZONE/happy_hour.json`

- `gif_to_json.py`: This Python script is used to create a single JSON animation file using an animated GIF
-- **Example:** `gif_to_json.py --input-gif nyan_cat.gif --output-json b134_extracted/STUPID/nyan_cat.json`

- `video_to_json.py`: This Python script is used to create a single JSON animation file using a video file
-- **Example:** `video_to_json.py --input rick_roll.mp4 --output-json b134_extracted/STUPID/rick_roll.json`

- `create_image.py`: This Python script is used to build a Run-DMD binary image from a directory of JSON files
-- **Example:** `create_image.py --input-dir b134_extracted --image custom_RunDMD_B134.img`

In addition to the items above, the repository also contains an animation editor in the "animation_editor" directory.  This is a simply HTML/Javascript tool that allows you to open an JSON file, edit the animation frame-by-frame, and save the file.  This is primarily useful for making small corrections to a JSON file, or for adding transparency to certain frames.  For larger edits, it is usually easier to simply remove the frame directly from the JSON file, or write a small helper script to edit the frames.

## Dependencies
With the exception of the gif_to_json.py and video_to_json.py scripts, there are no additional dependencies.  Those two scripts, however, require the PIL and imageio modules.

## Known Issues
The biggest known issue is with the way that frame duration is handled.  The extraction and creation both use a very simple guess as to how the frame duration is handled.  This seems to work when the frame duration is fairly short (less than ~100ms), but seems to fall apart for longer frame durations.  The Run-DMD firmware image is available on the web, so if somebody wants to disassemble the PIC firmware and fix the frame duration implementation, that would be useful.

## Future Developments
I had planned to release this years ago, but I wanted to iron out a few lingering issues.  Work, kids, and other life demands constantly got in the way, so I am just releasing this as-is.  I highly doubt I will ever have time to touch any of this again, so if somebody else wants to fork and take ownership, they are welcomed (and ecouraged!) to.

## License
Please consider this released under the MIT license.  Hack it, fork it, own it, etc.  Just do not blame me if it creates corrupt images for your Run-DMD clock :)

