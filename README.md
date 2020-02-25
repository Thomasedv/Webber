# Webber
A ffmpeg wrapper to cut and/crop videos to webm, while aiming for a filesize.
![Program](https://i.imgur.com/vQCPJLg.png)
## Disclaimer

I'm not well versed with setting up programs on other peoples computer, and this program needs some codecs to play specific video files, at present i can't and don't know how to provide these with the program itself, nor detect if they are missing, which means, if the codecs is missing it just won't work. Apparently K-Lite codec should have all the basic codecs or filter you need, but it's untested so far. If you have SVP (smooth video project) then you may be ok, as i got the required codecs support from that by coincidence. 

In general, this is a work to do a job, a tool of functionality, but it's just cobbled together, and for people other than me, probably way less intuitive to use. Read up on controls, make an issue if there is a question or problem. 

# Features

- Drag and drop video to program
- Set target output size of video
- Pick if you want to include audio or not. 
- Simple start and stop buttons for picking a trim point
- Right-Click video and drag down and right to box in the desired area you want to crop the video to. (Might be visually buggy, but it works despite the visuals) (BETA testing, to be improved on if needed)
- Can queue up multiple video conversions. As soon as the Convert button is pressed, and changes won't affect the queued video!
- Can cut without re-encoding straight to mp4. (Assuming ffmpeg can do it)

# Controls: 
- Press M to mute the video
- Use the scroll-wheel to increase/decrease the volume. 
- Left/Right skips 5 seconds forward/backwards. 

# How to use: 
- Drag video to load it. 
- Select start/end using the video position, and the buttons. (or input timestamp manually, do follow the format in use)
- Give it a name. Select options you want. 
- Click convert, and follow progress in the top left pane, wait til it says finished. 
