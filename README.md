# Webber
A ffmpeg wrapper to cut and/crop videos to webm, while aiming for a filesize.
![Program](https://i.imgur.com/MUKlhn5.png)

## Disclaimer

I'm not well versed with setting up programs on other peoples computer, and this program needs some codecs to play specific video files, at present i can't and don't know how to provide these with the program itself, nor detect if they are missing, which means, if the codecs is missing it just won't work. Apparently K-Lite codec should have all the basic codecs or filter you need, but it's untested so far. If you have SVP (smooth video project) then you may be ok, as i got the required codecs support from that by coincidence. 

In general, this is made to do a job, a tool of functionality, but it's just cobbled together, and for people other than me, probably way less intuitive to use. Read up on controls, make an issue if there is a question or problem. I'm happy to help! 

# Features
- VP9 or AV1 supported.
- Drag and drop video to program
- Set target output size of video
- Pick if you want to include audio or not. 
  - Uses 320kbps bitrate, may significantly reduce video quality to keep bitrate and filesize.
  - Can merge first 2 audio channels if you got game clips that have mic in second channel
- Simple start and stop buttons for picking a trim point. 
  - Eg. for dropping a game recording and picking just the parts that matter
- Right-Click video and drag down and right to box in the desired area you want to crop the video to. 
  - BETA: Might be visually buggy, but it works despite the visuals testing, to be improved on if desired.
- Can queue up multiple video conversions. As soon as the Convert button is pressed, any changes won't affect the queued video!
- Can cut without re-encoding straight to mp4. (Assuming ffmpeg can do it)
- Advanced: Ctrl+E brings up a panel to change encoding options. Changes are lost once program closes. 

# Controls: 
- Press M to mute the video
- Use the scroll-wheel to increase/decrease the volume. 
- Left/Right skips 5 seconds forward/backwards. 
- (There are some focus issues, so you might need to click screen for some playback controls takes effect, to be improved if needed asked about, nothing motivates more than the burden of delivering a good product.)

# How to use: 
- Drag video to load it. 
- Select start/end using the video position, and the buttons. (or input timestamp manually, do follow the format in use)
- Give it a name. Select options you want. 
- Click convert, and follow progress in the top left pane, wait til it says finished. 

# TODO:

This is not a userfriendly program at the moment. There is a few major changes needed to make it easier to handle:
- Show proper errors when missing required codec, link to codec install site (3rd party however)
- Short video tutorial, or just image explaning buttons
- Bundle ffmpeg with program if possible. (Not sure how licenseing works for the compiled exes.)
- Tweak and save profiles! Some of you probably want maximum quality at the lowest size. 
- Really, fix other issues, like controls being intercepted by bad focus.
- Add low quality audio, 128 kbps audio may be significantly space saving for longer clips! (Please make an issue if you want it.)
