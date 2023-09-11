# FIX RAIDEN BOSS
<a href=""><img alt="" src="https://cdn.discordapp.com/attachments/1030715335910887425/1060179887933104229/raiden.png?width=838&height=417"></a>
- Author Ideal [NK#1321](https://discordapp.com/users/277117247523389450)
- Thank [SilentNightSound#7430](https://github.com/SilentNightSound) for the logic rewrite
- Thank HazrateGolabi#1364 for combine and make final script
- Thank [Albert Gold#2696](https://github.com/Alex-Au1) for update the code for merged mods
## requestment : 
- [Python](https://www.python.org/downloads/)
- [DOWNLOAD](https://github.com/nhok0169/Fix-Raiden-Boss/archive/refs/heads/nhok0169.zip) script on this github
## Let's Start !
### STEP 1:
- Copy [THIS](https://github.com/nhok0169/Fix-Raiden-Boss/blob/nhok0169/Fix-Raiden-Boss%202.0%20(for%20all%20user%20)/RaidenBossFix2.py) script into Raiden Mod Folder 
### STEP 2:
- Double click on the script or [open cmd](https://www.google.com/search?q=how+to+open+cmd+in+a+folder&oq=how+to+open+cmd) and type :
```python
python RaidenBossFix2.py
```
then enter
- make sure you only run it 1 time
### STEP 3:
- Open the game and enjoy it ( i didn't test it with merge and if you merge them you need to run script on all original folder before merge so if you have error just tell me )
### VIDEO TUTORIAL :
https://www.youtube.com/watch?v=29FM0GywcWA
### Update for merged mods
For merged mods, previously users would have to go run the program in each individual mod, then make a custom mapping function in the `merged.ini` to each individual generated _`RaidenShogunRemapBlend.buf`_ files

As a quality of life feature change, now the user can just run the program where the `merged.ini` is located.

This change is also compatible with mods that are not merged.

### Demo
(**IF THE LINKS DO NOT WORK OR HAVE EXPIRED, THE DEMO VIDEOS ARE ALSO IN THE ZIP FILE**)

#### Links
[Fixing Merged Mod](https://streamable.com/c8zi25)
[Compatible Fixing of Unmerged Mod](https://streamable.com/ymcn3o)

#### Zip File
[videos_of_basic_tests.zip](https://github.com/nhok0169/Fix-Raiden-Boss/files/12570065/videos_of_basic_tests.zip)

### Notes
- Most of the new code uses the original code's model, then wrapped the model with lots of infrastructure and software design for robustness.

 - Although it would be better practice to put the individual classes into separate files, we stick all our classes into one file to keep the simple UI of the user copying the program into their desired mod and running the program. For better organization and software design, it would be better to separate out the classes, but a new UI may need to be introduced.
