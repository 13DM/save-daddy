# save-daddy
Automatically autosaves your blend file every 5 minutes (default) with a timestamp appended to the filename and manages backups.

Due to Blenders buggy autosave not working most of the time, and losing too many projects I decided to make one that should work fairly constantly. This script avoids the Blender install location since Windows doesn't like saving to Program Files sometimes, and this avoids any temp directories as those can be cleared out and we lose our autosave files. If you are working with a unsaved file and do not have the default path populated to save the file, it will prompt you to save the file first so that you can continue autosaving. These autosave files do not alter the original save file, so if you find that you are working and autosave is going along and you make a big mess up and the autosave file ends up capturing that, you can still revert to the regular save file and not lose any progress or data (aside from the work you have done)

Please note that if you are working with unsaved files, these will overwrite eachothers backups!

The autosave files will be saved in the following naming format:

<filename>_DD%_MM%_YY%_HH%-mm% for example - savedfile_07_02_25_13-39.blend

There are three configurable settings:

- Save Interval : How frequently should we save the file. Default is 300 seconds or 5 minutes. The minimum is 1 minute, else we may run into locking the UI.
- Save File Amounts : How many autosave backups do you want to retain. Default is 1, but you can configure as many as wanted. Beware, this will essentially copy the file and start eating space on storage if you set it too high.
- Default Save Location : If the file has not been saved, it will default to this location instead of the blend file location. 

![image](https://github.com/user-attachments/assets/f8e16d66-ebb8-4247-b7d8-58d753f8bce3)

As of now this has only been tested on Blender 3.6.5, but should work on newer versions. If they do not please let me know and I can take a look at updating the script to work there. 
