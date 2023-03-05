# ScriptTree
A Qt FileTreeView of Maya and Motion Builder scripts. With ScriptTree you will be able to edit and run scripts 
quickly and conveniently.

![script tree in action in maya](https://raw.githubusercontent.com/rBrenick/script-tree/master/docs/example_image.PNG)

The design is for this to work in both Maya and Motion Builder. See below the status of the devlopment.

| | Windows| OSX| Linux |
| -----:|:-----:|:-----:| :-----:|
| Maya | X | X | X |
| MotionBuilder |  |  |  |

The poor mans <a href="http://zurbrigg.com/charcoal-editor-2">Charcoal Editor.</a>

# Feature
- Run Script
- Edit Script
- Show file in explorer
- Backup scripts


# Setup
## Install
If you work in a studio / with multiple people, I would recommend pointing the folder at a network path 
so it's easier to access scripts from any machine.

Maya scripts install
```
Extract script file into maya script path.
```
Python Install
```Python
import sys
sys.path.append(r"UNZIP_FOLDER\script-tree")
```
.Bat install
```
Run installer.bat (will create a .mod file in your maya/modules folder)
Restart Maya
```

## Dependents

###[QT.py](https://github.com/mottosso/Qt.py)

## Run 
To Run script tree run the following code inside Maya or MotionBuilder
```Python
import script_tree
script_tree.main()
```

---

# Change Log
```
2022-03-02
- Allow for OSX and Linx use.
- Switch over to QT.py
- Add correct Google style doc strings. 

2020-09-26 
- Rewrote the tool from scratch.
- Switch between 'Run Script' and 'Edit Script' for the double click action
- Search all scripts for a specific string with "Ctrl+Shift+F"
- Better integration to maya's docking procedures
- Re-open recently closed tabs with "Ctrl+Shift+T"
```



### Notes
_Special Thanks to Niels Vaes for adding some convenience stuff to this tool, and throwing me some good feature ideas._
