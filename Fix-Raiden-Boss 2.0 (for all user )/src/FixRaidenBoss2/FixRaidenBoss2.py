# Author: NK#1321 raiden boss fix, if you used it to fix your raiden pls give credit for "Nhok0169"
# Special Thanks:
#   nguen#2011 (for support)
#   SilentNightSound#7430 (for internal knowdege so wrote the blendCorrection code)
#   HazrateGolabi#1364 (for being awesome, and improving the code)
#   Albert Gold#2696 (for update the code for merged mods)


import os
import configparser
import re
import struct
import traceback
from typing import List, Callable, Optional, Union, Dict, Any, TypeVar, Hashable, Tuple, Set
from collections import deque
import argparse
import ntpath


VGRemap = {'0':'0','1':'1','2':'2','3':'3','4':'4','5':'5','6':'6','7':'7','8':'60','9':'61','10':'66','11':'67',
             '12':'8','13':'9','14':'10','15':'11','16':'12','17':'13','18':'14','19':'15','20':'16','21':'17',
             '22':'18','23':'19','24':'20','25':'21','26':'22','27':'23','28':'24','29':'25','30':'26','31':'27',
             '32':'28','33':'29','34':'30','35':'31','36':'32','37':'33','38':'34','39':'35','40':'36','41':'37',
             '42':'38','43':'39','44':'40','45':'41','46':'42','47':'94','48':'43','49':'44','50':'45','51':'46',
             '52':'47','53':'48','54':'49','55':'50','56':'51','57':'52','58':'53','59':'54','60':'55','61':'56',
             '62':'57','63':'58','64':'59','65':'114','66':'116','67':'115','68':'117','69':'74','70':'62','71':'64',
             '72':'106','73':'108','74':'110','75':'75','76':'77','77':'79','78':'87','79':'89','80':'91','81':'95',
             '82':'97','83':'99','84':'81','85':'83','86':'85','87':'68','88':'70','89':'72','90':'104','91':'112',
             '92':'93','93':'63','94':'65','95':'107','96':'109','97':'111','98':'76','99':'78','100':'80','101':'88',
             '102':'90','103':'92','104':'96','105':'98','106':'100','107':'82','108':'84','109':'86','110':'69',
             '111':'71','112':'73','113':'105','114':'113','115':'101','116':'102','117':'103'}
MaxVGIndex = 117

# change our current working directory to this file, allowing users to run program
#   by clicking on the script instead of running by CLI
if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

DefaultFileType = "file"
DefaultPath = os.getcwd()
CurrentDir = "."
IniExt = ".ini"
TxtExt = ".txt"
BufExt = ".buf"
IniExtLen = len(IniExt)
MergedFile = f"merged{IniExt}"
BackupFilePrefix = "DISABLED_RSFixBackup_"
DuplicateFilePrefix = "DISABLED_RSDup_"
LogFile = f"RSFixLog{TxtExt}"

IniFileType = "*.ini file"
BlendFileType = f"Blend{BufExt}"
RemapBlendFile = f"Remap{BlendFileType}"
IniFileEncoding = "utf-8"
ReadEncodings = [IniFileEncoding, "latin1"]

Deprecated = "DEPRECATED"

DeleteBackupOpt = '--deleteBackup'
FixOnlyOpt = '--fixOnly'
RevertOpt = '--revert'
AllOpt = '--all'
argParser = argparse.ArgumentParser(description='Fixes Raiden Boss Phase 1 for all types of mods', formatter_class=argparse.MetavarTypeHelpFormatter)
argParser.add_argument('-s', '--src', action='store', type=str, help="The path to the Raiden mod folder. If this option is not specified, then will use the current directory as the mod folder.")
argParser.add_argument('-d', DeleteBackupOpt, action='store_true', help=f'deletes backup copies of the original {IniExt} files')
argParser.add_argument('-f', FixOnlyOpt, action='store_true', help='only fixes the mod without cleaning any previous runs of the script')
argParser.add_argument('-r', RevertOpt, action='store_true', help='reverts back previous runs of the script')
argParser.add_argument('-l', '--log', action='store_true', help=f'Logs the printed out log into a seperate {TxtExt} file')
argParser.add_argument('-a', AllOpt, action='store_true', help=f'Parses all {IniFileType}s that the program encounters instead of only parsing {IniFileType}s that have the section [TextureOverrideRaidenShogunBlend]')

T = TypeVar('T')


class Error(Exception):
    def __init__(self, message: str):
        super().__init__(f"ERROR: {message}")

    def warn(self):
        return str(self).replace("ERROR", "WARNING")


class FileException(Error):
    def __init__(self, message: str, path: str = DefaultPath):
        if (path != DefaultPath):
            message += f" at {path}"

        super().__init__(message)


class DuplicateFileException(FileException):
    def __init__(self, files: List[str], fileType: str = DefaultFileType, path: str = DefaultPath):
        self.files = files
        self.fileType = fileType
        message = f"Ensure only one {fileType} exists"
        super().__init__(message, path = path)


class MissingFileException(FileException):
    def __init__(self, fileType: str = DefaultFileType, path: str = DefaultPath):
        message = f"Unable to find {fileType}. Ensure it is in the folder"
        self.fileType = fileType
        super().__init__(message, path = path)


class BlendFileNotRecognized(FileException):
    def __init__(self, blendFile: str):
        super().__init__(f"Blend file format not recognized for {os.path.basename(blendFile)}", path = os.path.dirname(blendFile))


class ConflictingOptions(Error):
    def __init__(self, options: List[str]):
        optionsStr = ", ".join(options)
        super().__init__(f"The following options cannot be used toghether: {optionsStr}")


class DictTools():
    @classmethod
    def getFirstKey(cls, dict: Dict[Any, Any]) -> Any:
        return next(iter(dict))

    @classmethod
    def getFirstValue(cls, dict: Dict[Any, Any]) -> Any:
        return dict[cls.getFirstKey(dict)]
    
    # combine(dst, src, combine_duplicate): Combines dictionaries to 'dst'
    @classmethod
    def combine(cls, dst: Dict[Hashable, Any], src: Dict[Hashable, Any], combineDuplicate: Optional[Callable[[Any, Any], Any]] = None):
        if (combineDuplicate is None):
            dst.update(src)
            return dst
        
        new_dict = {**dst, **src}
        for key, value in new_dict.items():
            if key in dst and key in src:
                new_dict[key] = combineDuplicate(value, src[key])
        return new_dict
    

class ListTools():
    @classmethod
    def to_dict(cls, lst: List[T], get_id: Callable[[T], Hashable]) -> Dict[Hashable, T]:
        return {get_id(e): e for e in lst}

    @classmethod
    def getDistinct(cls, lst: List[T]):
        return list(dict.fromkeys(lst))


class FileService():
    @classmethod
    def getFilesAndDirs(cls, path: str = DefaultPath, recursive: bool = False) -> List[List[str]]:
        files = []
        dirs = []

        pathItems = []
        
        if (recursive):
            for root, currentDirs, currentFiles in os.walk(path, topdown = True):
                for dir in currentDirs:
                    dirs.append(os.path.join(root, dir))

                for file in currentFiles:
                    files.append(os.path.join(root, file))

            return [files, dirs]
        
        pathItems = os.listdir(path)
        for itemPath in pathItems:
            fullPath = os.path.join(path, itemPath)
            if (os.path.isfile(fullPath)):
                files.append(fullPath)
            else:
                dirs.append(fullPath)

        return [files, dirs]

    @classmethod
    def isFile(cls, path: str, file: str) -> bool:
        fullPath = os.path.join(path, file)
        return os.path.isfile(fullPath)

    # filters and partitions the files based on the different filters specified
    @classmethod
    def getFiles(cls, path: str = DefaultPath, filters: List[Callable[[str], bool]] = [], files: Optional[List[str]] = None) -> Union[List[str], List[List[str]]]:
        result = []

        if (not filters):
            filters.append(lambda itemPath: True)

        pathFilters = []
        filtersLen = len(filters)

        usePathFiles = False
        if (files is None):
            files = os.listdir(path)
            usePathFiles = True

        for i in range(filtersLen):
            filter = filters[i]
            result.append([])

            if (usePathFiles):
                newFilter = lambda itemPath: filters[i](itemPath) and cls.isFile(path, itemPath)
            else:
                newFilter = filter

            pathFilters.append(newFilter)

        for itemPath in files:
            for filterInd in range(filtersLen):
                pathFilter = filters[filterInd]
                if (not pathFilter(itemPath)):
                    continue
                
                fullPath = itemPath
                if (usePathFiles):
                    fullPath = os.path.join(path, itemPath)

                result[filterInd].append(fullPath)

        if (filtersLen == 1):
            return result[0]
        
        return result
    
    # retrieves only a single file for each filetype specified by the filters
    @classmethod
    def getSingleFiles(cls, path: str = DefaultPath, filters: Dict[str, Callable[[str], bool]] = {}, files: Optional[List[str]] = None, optional: bool = False) -> Optional[Union[str, List[str], List[Optional[str]]]]:
        if (not filters):
            filters[DefaultFileType] = lambda itemPath: True
        
        filesPerFileTypes = cls.getFiles(path = path, filters = list(filters.values()), files = files)
        filtersLen = len(filters)

        onlyOneFilter = filtersLen == 1
        if (onlyOneFilter):
            filesPerFileTypes = [filesPerFileTypes]

        result = []
        i = 0
        for fileType in filters:
            fileTypeFiles = filesPerFileTypes[i]
            filesLen = len(fileTypeFiles)

            if (not optional and not filesLen):
                raise MissingFileException(fileType = fileType, path = path)
            elif (not optional and filesLen > 1):
                raise DuplicateFileException(fileTypeFiles, fileType = fileType, path = path)
            
            if (fileTypeFiles):
                result.append(fileTypeFiles[0])
            else:
                result.append(None)
            i += 1

        if (onlyOneFilter):
            return result[0]
        
        return result
    
    @classmethod
    def rename(cls, oldFile: str, newFile: str):
        try:
            os.rename(oldFile, newFile)
        except FileExistsError:
            os.remove(newFile)
            os.rename(oldFile, newFile)

    @classmethod
    def changeExt(cls, file: str, newExt: str):
        dotPos = file.rfind(".")

        if (not newExt.startswith(".")):
            newExt = f".{newExt}"

        if (dotPos != -1):
            file = file[:dotPos] + newExt

        return file

    @classmethod
    def disableFile(cls, file: str, filePrefix: str = BackupFilePrefix):
        baseName = os.path.basename(file)
        baseName = FileService.changeExt(baseName, TxtExt)

        backupFile = os.path.join(os.path.dirname(file), filePrefix) + baseName
        FileService.rename(file, backupFile)

    @classmethod
    def parseOSPath(cls, path: str):
        result = ntpath.normpath(path)
        result = cls.ntPathToPosix(result)
        return result

    @classmethod
    def ntPathToPosix(cls, path: str) -> str:
        return path.replace(ntpath.sep, os.sep)
    
    @classmethod
    def absPathOfRelPath(cls, dstPath: str, relFolder: str) -> str:
        relFolder = os.path.abspath(relFolder)
        result = dstPath
        if (not os.path.isabs(result)):
            result = os.path.join(relFolder, result)
            result = cls.parseOSPath(result)

        return result
    
    @classmethod
    def getRelPath(cls, path: str, start: str) -> str:
        result = path
        try:
            result = os.path.relpath(path, start)

        # if the path is in another mount than 'start'
        except ValueError:
            pass

        return result
    
    # read(file, fileCode, postProcessor): Tries to read a file using different encodings
    @classmethod
    def read(cls, file: str, fileCode: str, postProcessor: Callable[[Any], Any]):
        for encoding in ReadEncodings:
            try:
                with open(file, fileCode, encoding = encoding) as f:
                    return postProcessor(f)
            except UnicodeDecodeError:
                pass


class Logger():
    DefaultHeadingSideLen = 2
    DefaultHeadingChar = "="

    def __init__(self, prefix: str = "", logTxt: bool = False, verbose: bool = True):
        self._prefix = prefix
        self._headingTxtLen = 0
        self._headingSideLen = 0
        self._headingChar = ""
        self.includePrefix = True
        self.verbose = verbose
        self.logTxt = logTxt
        self._loggedTxt = ""
        self._currentPrefixTxt = ""

        self._setDefaultHeadingAtts()

    @property
    def prefix(self):
        return self._prefix
    
    @prefix.setter
    def prefix(self, newPrefix):
        self._prefix = newPrefix
        self._currentPrefixTxt = ""

    @property
    def loggedTxt(self):
        return self._loggedTxt

    def _setDefaultHeadingAtts(self):
        self._headingTxtLen = 0
        self._headingSideLen = self.DefaultHeadingSideLen
        self._headingChar = self.DefaultHeadingChar

    def _addLogTxt(self, txt: str):
        if (self.logTxt):
            self._loggedTxt += f"{txt}\n"

    def getStr(self, message: str):
        return f"# {self._prefix} --> {message}"

    def log(self, message: str):
        if (not self.verbose):
            return

        if (self.includePrefix):
            message = self.getStr(message)

        self._addLogTxt(message)
        self._currentPrefixTxt += message
        print(message)

    def split(self):
        if (self._currentPrefixTxt):
            self.log("\n")

    def space(self):
        self.log("")

    def openHeading(self, txt: str, sideLen: int = DefaultHeadingSideLen, headingChar = DefaultHeadingChar):
        self._headingTxtLen = len(txt)
        self._headingSideLen = sideLen
        self._headingChar = headingChar
        
        side = headingChar * sideLen
        self.log(f"{side} {txt} {side}")

    def closeHeading(self):
        side = self._headingChar * self._headingSideLen
        mid = self._headingChar * (self._headingTxtLen + 2)
        self.log(f"{side}{mid}{side}")

        self._setDefaultHeadingAtts()

    @classmethod
    def getBulletStr(self, txt: str) -> str:
        return f"- {txt}"
    
    @classmethod
    def getNumberedStr(self, txt: str, num: int) -> str:
        return f"{num}. {txt}"

    def bulletPoint(self, txt: str):
        self.log(self.getBulletStr(txt))

    def list(self, lst: List[str], transform: Optional[Callable[[str], str]] = None):
        if (transform is None):
            transform = lambda txt: txt

        lstLen = len(lst)
        for i in range(lstLen):
            newTxt = transform(lst[i])
            self.log(self.getNumberedStr(newTxt, i + 1))

    def box(self, message: str, header: str):
        self.log(header)

        messageList = message.split("\n")
        for messagePart in messageList:
            self.log(messagePart)

        self.log(header)

    def error(self, message: str):
        self.space()
        prevVerbose = self.verbose
        self.verbose = True

        self.box(message, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        self.space()
        self.verbose = prevVerbose

    def note(self, message: str):
        self.space()
        self.box(f"Note: {message}", "*****************************")

    @classmethod
    def getWarnStr(self, exception: Error) -> str:
        return f"{type(exception).__name__}: {exception.warn()}"
    
    def warn(self, exception: Error):
        self.error(self.getWarnStr(exception))

    def handleException(self, exception: BaseException):
        message = f"\n{type(exception).__name__}: {exception}\n\n{traceback.format_exc()}"
        self.error(message)

    def input(self, desc: str) -> str:
        if (self.includePrefix):
            desc = self.getStr(desc)

        self._addLogTxt(desc)
        result = input(desc)
        self._addLogTxt(f"Input: {result}")

        return result

    def waitExit(self):
        prevIncludePrefix = self.includePrefix
        self.includePrefix = False
        self.input("\n== Press ENTER to exit ==")
        self.includePrefix = prevIncludePrefix 


# our model objects in MVC
class Model():
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger

    def print(self, funcName: str, *args, **kwargs):
        if (self.logger is not None):
            func = getattr(self.logger, funcName)
            return func(*args, **kwargs)


# Needed data model to inject into the .ini file
class RemapBlendModel():
    def __init__(self, iniFolderPath: str, fixedBlendName: str, fixedBlendPaths: Dict[int, str], origBlendName: Optional[str] = None,
                 origBlendPaths: Optional[Dict[int, str]] = None):
        self.fixedBlendName = fixedBlendName
        self.fixedBlendPaths = fixedBlendPaths
        self.origBlendName = origBlendName
        self.origBlendPaths = origBlendPaths
        self.iniFolderPath = iniFolderPath

        self.fullPaths = {}
        self.origFullPaths = {}

        # retrieve the absolute paths
        for partIndex in self.fixedBlendPaths:
            path = self.fixedBlendPaths[partIndex]
            self.fullPaths[partIndex] = FileService.absPathOfRelPath(path, iniFolderPath)

        for partIndex in self.origBlendPaths:
            path = self.origBlendPaths[partIndex]
            self.origFullPaths[partIndex] = FileService.absPathOfRelPath(path, iniFolderPath)


# IfTemplate: Data class for the if..else template of the .ini file
class IfTemplate():
    def __init__(self, parts: List[Union[str, Dict[str, Any]]], calledSubCommands: Optional[Dict[int, str]] = None):
        self.parts = parts
        self.calledSubCommands = calledSubCommands

        if (calledSubCommands is None):
            self.calledSubCommands = {}

    def __iter__(self):
        return self.parts.__iter__()
    
    def __getitem__(self, key):
        return self.parts[key]
    
    def __setitem__(self, key, value):
        self.parts[key] = value

    def add(self, part: Union[str, Dict[str, Any]]):
        self.parts.append(part)

    # find(pred, postProcessor): Searches each part in the if template based on 'pred'
    def find(self, pred: Optional[Callable[[Union[str, Dict[str, Any]]], bool]] = None, postProcessor: Optional[Callable[[Union[str, Dict[str, Any]]], Any]] = None) -> Dict[int, Any]:
        result = {}
        if (pred is None):
            pred = lambda part: True

        if (postProcessor is None):
            postProcessor = lambda part: part

        partsLen = len(self.parts)
        for i in range(partsLen):
            part = self.parts[i]
            if (pred(part)):
                result[i] = (postProcessor(part))

        return result


# IniFile: Class to handle .ini files
#
# Note: We analyse the .ini file using Regex which is NOT the right way to do things
#   since the modified .ini language that GIMI interprets is a CFG (context free grammer) and NOT a regular language.
#   
#   But since we are lazy and don't want make our own compiler with tokenizers, parsing algorithms (eg. SLR(1)), type checking, etc...
#       this module should handle regular cases of .ini generated using existing scripts (assuming the user does not do anything funny...)
class IniFile(Model):
    Credit = f'\n; Raiden boss fixed by NK#1321 if you used it for fix your raiden pls give credit for "Nhok0169"\n; Thank nguen#2011 SilentNightSound#7430 HazrateGolabi#1364 and Albert Gold#2696 for support'

    _fixHeader = "; --------------- Raiden Boss Fix -----------------"
    _fixFooter = "; -------------------------------------------------"

    Hash = "hash"
    Vb1 = "vb1"
    Handling = "handling"
    Draw = "draw"
    Resource = "Resource"
    Blend = "Blend"
    Run = "run"
    RemapBlend = f"Remap{Blend}"

    # -- regex strings ---

    _textureOverrideRaidenBlendPatternStr = r"\[\s*TextureOverride.*(Raiden|Shogun).*" + Blend + r"\s*\]"
    _textureOverrideBlendPatternStr = r"\[\s*TextureOverride.*" + Blend + r".*\s*\]"
    _fixedTextureOverrideBlendPatternStr = r"\[\s*TextureOverride.*" + RemapBlend + r"\s*\]"

    # --------------------
    # -- regex objects ---
    _sectionPattern = re.compile(r"\[.*\]")
    _textureOverrideRaidenBlendPattern  = re.compile(_textureOverrideRaidenBlendPatternStr)
    _textureOverrideBlendPattern = re.compile(_textureOverrideBlendPatternStr)
    _fixedTextureOverrideBlendPattern = re.compile(_fixedTextureOverrideBlendPatternStr)
    _fixRemovalPattern = re.compile(f"{_fixHeader}(.|\n)*{_fixFooter}")
    _removalPattern = re.compile(f"({_fixedTextureOverrideBlendPatternStr})|(\[.*" + RemapBlend + r".*\])")

    # -------------------

    _ifStructurePattern = re.compile(r"\s*(endif|if|else)")

    def __init__(self, file: str, logger: Optional[Logger] = None):
        super().__init__(logger = logger)
        self.file = file
        self._parser = configparser.ConfigParser()

        self._fileLines = []
        self._fileTxt = ""
        self._fileLinesRead = False
        self._isRaidenFixed = False
        self._isRaidenIni = False

        self._textureOverrideBlendRoot = ""
        self._sectionIfTemplates: Dict[str, IfTemplate] = {}
        self._resourceBlends: Dict[str, IfTemplate] = {}
        self._blendCommands: Dict[str, IfTemplate] = {}
        self._blendCommandsRemapNames: Dict[str, str] = {}
        self._blendCommandsTuples: List[Tuple[str]] = []

        self.remapBlendModelsDict: Dict[str, RemapBlendModel] = {}
        self.remapBlendModels: List[RemapBlendModel] = []

    @property
    def isRaidenFixed(self):
        return self._isRaidenFixed
    
    @property
    def isRaidenIni(self):
        return self._isRaidenIni

    def clearRead(self):
        self._fileLines = []
        self._fileLinesRead = False
        self._isRaidenFixed = False

    def read(self) -> str:
        result = ""
        result = FileService.read(self.file, "r", lambda filePtr: filePtr.read())
        return result
    
    def write(self):
        txtToWrite = "".join(self._fileLines)
        with open(self.file, "w", encoding = IniFileEncoding) as f:
            f.write(txtToWrite)

    @classmethod
    def copy(cls, srcIniFile):
        assert(isinstance(srcIniFile, IniFile))
        return cls(srcIniFile.file, logger = srcIniFile.logger, merged = srcIniFile.merged)

    def getFileLines(self) -> List[str]:
        self._fileLines = FileService.read(self.file, "r", lambda filePtr: filePtr.readlines())
        self._fileLinesRead = True
        return self._fileLines

    def _readLines(func):
        def readLinesWrapper(self, *args, **kwargs):
            if (not self._fileLinesRead):
                self.getFileLines()
            return func(self, *args, **kwargs)
        return readLinesWrapper
    
    def checkRaidenIni(self, isRaidenIni = False):
        postProcessor = lambda startInd, endInd, fileLines, sectionName, srcTxt: sectionName
        textureOverridePattern = self._textureOverrideRaidenBlendPattern
        if (isRaidenIni):
            textureOverridePattern = self._textureOverrideBlendPattern

        textureOverrideBlendSections = self.getSectionOptions(textureOverridePattern , postProcessor = postProcessor)

        self._isRaidenIni = bool(textureOverrideBlendSections)
        if (self._isRaidenIni):
            self._textureOverrideBlendRoot = DictTools.getFirstKey(textureOverrideBlendSections)

    def _checkRaidenFixed(self, line: str):
        if (not self._isRaidenFixed and self._fixedTextureOverrideBlendPattern.match(line)):
            self._isRaidenFixed = True

    def _parseSection(self, sectionName: str, srcTxt: str, save: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, str]]:
        try:
            self._parser.read_string(srcTxt)
        except:
            return None

        result = dict(self._parser[sectionName])

        try:
            save[sectionName] = result
        except TypeError:
            pass

        return result

    # retrieves the key-value pairs of a section in the .ini file. Manually parsed the file since ConfigParser
    #   errors out on conditional statements in .ini file for mods. Could later inherit from the parser (RawConfigParser) 
    #   to custom deal with conditionals
    @_readLines
    def getSectionOptions(self, section: Union[str, Callable[[str], bool]], postProcessor: Optional[Callable[[int, int, List[str], str, str], Any]] = None) -> Dict[str, Dict[str, Any]]:
        sectionFilter = None
        if (isinstance(section, str)):
            sectionFilter = lambda line: line == section
        elif callable(section):
            sectionFilter = section
        else:
            sectionFilter = lambda line: section.match(line)

        if (postProcessor is None):
            postProcessor = lambda startInd, endInd, fileLines, sectionName, srcTxt: self._parseSection(sectionName, srcTxt)

        result = {}
        currentSectionName = None
        currentSectionToParse = None
        currentSectionStartInd = -1

        fileLinesLen = len(self._fileLines)

        for i in range(fileLinesLen):
            line = self._fileLines[i]
            self._checkRaidenFixed(line)

            if (sectionFilter(line)):
                currentSectionToParse = f"{line}"
                currentSectionName = line.strip().replace("]", "")
                currentSectionName = currentSectionName.replace("[", "")
                currentSectionStartInd = i
                continue

            if (currentSectionToParse is None):
                continue

            if (line.strip() == ""):
                currentResult = postProcessor(currentSectionStartInd, i, self._fileLines, currentSectionName, currentSectionToParse)
                if (currentResult is None):
                    continue

                result[currentSectionName] = currentResult

                currentSectionToParse = None
                currentSectionName = None
                currentSectionStartInd = -1
            else:
                currentSectionToParse += f"{line}"

        # get any remainder section
        if (currentSectionToParse is not None):
            result[currentSectionName] = postProcessor(currentSectionStartInd, fileLinesLen, self._fileLines, currentSectionName, currentSectionToParse)

        return result

    def _removeSection(self, startInd: int, endInd: int, fileLines: List[str], sectionName: str, srcTxt: str):
        if (endInd >= len(fileLines)):
            return (startInd, endInd)
        return (startInd, endInd + 1)
    
    def removeSectionOptions(self, section: str):
        rangesToRemove = self.getSectionOptions(section, postProcessor = self._removeSection)

        for sectionName in rangesToRemove:
            range = rangesToRemove[sectionName]
            startInd = range[0]
            endInd = range[1]

            self._fileLines[startInd:endInd] =  [0] * (endInd - startInd)

        self._fileLines = filter(lambda line: line != 0, self._fileLines)

    def _processIfTemplate(self, startInd: int, endInd: int, fileLines: List[str], sectionName: str, srcTxt: str) -> IfTemplate:
        ifTemplate = []
        dummySectionName = "dummySection"
        currentDummySectionName = f"{dummySectionName}"
        replaceSection = ""
        atReplaceSection = False

        for i in range(startInd + 1, endInd):
            line = fileLines[i]
            isConditional = bool(self._ifStructurePattern.match(line))

            if (isConditional and atReplaceSection):
                currentDummySectionName = f"{dummySectionName}{i}"
                replaceSection = f"[{currentDummySectionName}]\n{replaceSection}"

                currentPart = self._parseSection(currentDummySectionName, replaceSection)
                if (currentPart is None):
                    currentPart = {}

                ifTemplate.append(currentPart)
                replaceSection = ""

            if (isConditional):
                ifTemplate.append(line)
                atReplaceSection = False
                continue
            
            replaceSection += line
            atReplaceSection = True

        # get any remainder replacements in the if..else template
        if (replaceSection != ""):
            currentDummySectionName = f"{dummySectionName}END{endInd}"
            replaceSection = f"[{currentDummySectionName}]\n{replaceSection}"
            currentPart = self._parseSection(currentDummySectionName, replaceSection)
            if (currentPart is None):
                currentPart = {}

            ifTemplate.append(currentPart)

        # get all the sections called by the current section
        result = IfTemplate(ifTemplate)
        calledSubCommands = result.find(pred = lambda part: isinstance(part, dict) and self._isIfTemplateSubCommand(part), postProcessor = self._getIfTemplateSubCommand)
        result.calledSubCommands = calledSubCommands

        return result
                
    
    @classmethod
    def getMergedResourceIndex(cls, mergedResourceName: str) -> str:
        return mergedResourceName.rsplit(".", 1)[-1]
    
    def _getResourceSortKey(self, resourceTuple: Tuple[str, Any]) -> int:
        result = -1
        try:
            result = int(self.getMergedResourceIndex(resourceTuple[0]))
        except:
            pass

        return result

    # get the sorted order of the mod folders used in the merged.ini
    def getResourceBlendFolderPaths(self, resourceDicts: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, str]:
        fileNameKey = "filename"
        modFoldersDict = {}

        if (resourceDicts is None):
            resourceDicts = self._resourceBlends

        # case where the resources are not put in the proper order
        resourceTuples = [(k, v) for k, v in resourceDicts.items()]
        resourceTuples.sort(key = self._getResourceSortKey)

        for tuple in resourceTuples:
            resourceName = tuple[0]
            resourceDict = tuple[1]

            # normalize by ntpath for linux users
            if (resourceDict[fileNameKey]):
                resourcePath = ntpath.normpath(resourceDict[fileNameKey])
                folderPath = ntpath.dirname(resourcePath)
                modFoldersDict[resourceName] = folderPath

        return modFoldersDict

    # Disabling the OLD ini
    def disIni(self):
        FileService.disableFile(self.file)

    @classmethod
    def getFixedBlendFile(cls, blendFile: str) -> str:
        blendFile = blendFile.rsplit(".", 1)[0]
        blendFolder = os.path.dirname(blendFile)
        blendBaseName = os.path.basename(blendFile)
        
        return os.path.join(blendFolder, f"{cls.getRemapName(blendBaseName)}.buf")

    @classmethod
    def getFixHeader(cls) -> str:
        return cls._fixHeader
    
    @classmethod
    def getFixFooter(cls) -> str:
        return f"\n\n{cls._fixFooter}"

    def _addFixBoilerPlate(func):
        def addFixBoilerPlateWrapper(self, *args, **kwargs):
            addFix = self.getFixHeader()
            addFix += self.Credit
            addFix += func(self, *args, **kwargs)
            addFix += self.getFixFooter()

            return addFix
        return addFixBoilerPlateWrapper
    
    @classmethod
    def getResourceName(cls, name: str) -> str:
        return f"{cls.Resource}{name}"
    
    @classmethod
    def removeResourceName(cls, name: str) -> str:
        if (name.startswith(cls.Resource)):
            name = name[len(cls.Resource):]

        return name
    
    @classmethod
    def getRemapName(cls, name: str) -> str:
        nameParts = name.rsplit(cls.Blend, 1)
        namePartsLen = len(nameParts)

        if (namePartsLen > 1):
            name = cls.RemapBlend.join(nameParts)
        else:
            name += cls.RemapBlend

        return name

    @classmethod
    def getRemapResourceName(cls, name: str) -> str:
        name = cls.getRemapName(name)
        if (not name.startswith(cls.Resource)):
            name = cls.getResourceName(name)

        return name

    @classmethod
    def addTabs(cls, txt: str, tabCount: int = 0):
        tabs = "\t" * tabCount
        return f"{tabs}{txt}"
    
    @classmethod
    def getFixMapping(cls, blendName: str, draw: int, tabCount: int = 1) -> str:
        tabs = "\t" * tabCount
        return f"{tabs}{cls.Vb1} = {blendName}\n{tabs}handling = skip\n{tabs}{cls.Draw} = {draw}"

    def _isIfTemplateResource(self, ifTemplatePart: Dict[str, Any]) -> bool:
        return self.Vb1 in ifTemplatePart
    
    def _isIfTemplateDraw(self, ifTemplatePart: Dict[str, Any]) -> bool:
        return self.Draw in ifTemplatePart
    
    def _isIfTemplateSubCommand(self, ifTemplatePart: Dict[str, Any]) -> bool:
        return self.Run in ifTemplatePart
    
    def _getIfTemplateResourceName(self, ifTemplatePart: Dict[str, Any]) -> Any:
        return ifTemplatePart[self.Vb1]
    
    def _getIfTemplateSubCommand(self, ifTemplatePart: Dict[str, Any]) -> Any:
        return ifTemplatePart[self.Run]
    
    # fills the attributes for the sections related to the texture override blend
    def fillTextureOverrideRemapBlend(self, sectionName: str, part: Dict[str, Any], partIndex: int, tabCount: int, origSectionName: str):
        addFix = ""

        for varName in part:
            varValue = part[varName]

            # filling in the subcommand
            addFix += self.fillSubCommand(varName, varValue, tabCount)

            # filling in the hash
            if (varName == self.Hash):
                addFix += f"{self.addTabs('hash = fe5c0180', tabCount = tabCount)}\n"

            # filling in the vb1 resource
            elif (varName == self.Vb1):
                blendName = self._getIfTemplateResourceName(part)
                remapModel = self.remapBlendModelsDict[blendName]
                fixStr = f'{self.Vb1} = {remapModel.fixedBlendName}'
                addFix += f"{self.addTabs(fixStr, tabCount = tabCount)}\n"

            # filling in the handling
            elif (varName == self.Handling):
                fixStr = f'{self.Handling} = skip'
                addFix += f"{self.addTabs(fixStr, tabCount = tabCount)}\n"

            # filling in the draw value
            elif (varName == self.Draw):
                fixStr = f'{self.Draw} = {varValue}'
                addFix += f"{self.addTabs(fixStr, tabCount = tabCount)}\n"

        return addFix
    
    # fill the attributes for the sections related to the resources
    def fillRemapResource(self, sectionName: str, part: Dict[str, Any], partIndex: int, tabCount: int, origSectionName: str):
        addFix = ""
        fileAdded = False

        for varName in part:
            varValue = part[varName]

            # filling in the subcommand
            addFix += self.fillSubCommand(varName, varValue, tabCount)

            # add in the file only once
            if (not fileAdded and "filename" in part):
                remapModel = self.remapBlendModelsDict[origSectionName]
                fixedBlendFile = remapModel.fixedBlendPaths[partIndex]
                resourceStr = f"type = Buffer\nstride = 32\nfilename = {fixedBlendFile}"
                addFix += f"{self.addTabs(resourceStr)}\n"

                fileAdded = True

        return addFix

    # fills any called subcommands
    def fillSubCommand(self, varName: str, varValue: str, tabCount: int):
        addFix = ""
        if (varName == self.Run):
            subCommandStr = f"{self.Run} = {self._blendCommandsRemapNames[varValue]}"
            addFix += f"{self.addTabs(subCommandStr, tabCount = tabCount)}\n"

        return addFix
    
    # fills the if..else template in the .ini for each section
    def fillIfTemplate(self, sectionName: str, ifTemplate: IfTemplate, fillFunc: Callable[[str, Union[str, Dict[str, Any]], int, int, str], str], origSectionName: Optional[str] = None):
        addFix = f"[{sectionName}]\n"
        tabCount = 0
        partIndex = 0

        if (origSectionName is None):
            origSectionName = sectionName

        for part in ifTemplate:
            # adding in the if..else statements
            if (isinstance(part, str)):
                addFix += part
                
                linePrefix = re.match(r"^[\t]*[^\s]*", part)
                if (linePrefix):
                    linePrefix = linePrefix.group(0)
                    tabCount = linePrefix.count("\t")

                    if (linePrefix.find("endif") == -1):
                        tabCount += 1
                continue
            
            # add in the content within the if..else statements
            addFix += fillFunc(sectionName, part, partIndex, tabCount, origSectionName)

            partIndex += 1
            
        return addFix

    # get the needed lines to fix the .ini file
    @_addFixBoilerPlate
    def getFixStr(self, fix: str = "") -> str:
        hasResouces = bool(self.remapBlendModels)
        if (self._blendCommands or hasResouces):
            fix += "\n\n"

        # get the fix string for all the texture override blends
        for commandTuple in self._blendCommandsTuples:
            section = commandTuple[0]
            ifTemplate = commandTuple[1]
            commandName = self.getRemapName(section)
            fix += self.fillIfTemplate(commandName, ifTemplate, self.fillTextureOverrideRemapBlend)
            fix += "\n"

        if (hasResouces):
            fix += "\n"

        # get the fix string for the resources
        resourceBlendLen = len(self.remapBlendModels)
        for i in range(resourceBlendLen):
            remapModel = self.remapBlendModels[i]
            section = remapModel.origBlendName

            ifTemplate = self._resourceBlends[section]
            resourceName = remapModel.fixedBlendName
            fix += self.fillIfTemplate(resourceName, ifTemplate, self.fillRemapResource, origSectionName = section)

            if (i < resourceBlendLen - 1):
                fix += "\n"

        return fix

    @_readLines
    def injectAddition(self, addition: str, beforeOriginal: bool = True, keepBackup: bool = True, fixOnly: bool = False):
        original = "".join(self._fileLines)

        if (keepBackup and fixOnly):
            self.print("log", "Cleaning up and disabling the OLD STINKY ini")
            self.disIni()

        # writing the fixed file
        with open(self.file, "w", encoding = IniFileEncoding) as f:
            if (beforeOriginal):
                f.write(f"{addition}\n\n")

            f.write(original)

            if (not beforeOriginal):
                f.write(addition)

        self._isRaidenFixed = True

    @_readLines
    def _removeScriptFix(self):
        fileTxt = "".join(self._fileLines)
        fileTxt = re.sub(self._fixRemovalPattern, "", fileTxt)
        fileTxt = fileTxt.strip()

        with open(self.file, "w", encoding = IniFileEncoding) as f:
            f.write(fileTxt)

        self.clearRead()

    def _removeFix(self):
        self._removeScriptFix()        
        if (not self._fileLinesRead):
            self.getFileLines()

        self.removeSectionOptions(self._removalPattern)
        self.write()
        self.clearRead()

    @_readLines
    def removeFix(self, keepBackups: bool = True, fixOnly: bool = False):
        if (keepBackups and not fixOnly):
            self.print("log", f"Creating Backup for {os.path.basename(self.file)}")
            self.disIni()

        self.print("log", f"Removing any previous changes from this script in {os.path.basename(self.file)}")
        self._removeFix()

    def processSection(self, startInd: int, endInd: int, fileLines: List[str], sectionName: str, srcTxt: str):
        pass

    def _makeRemapModels(self):
        folderPath = os.path.dirname(self.file)
        
        for resourceKey in self._resourceBlends:
            resourceIftemplate = self._resourceBlends[resourceKey]
            fixedBlendName = self.getRemapResourceName(resourceKey)
            origBlendPaths = {}
            fixedBlendPaths = {}

            partIndex = 0
            for part in resourceIftemplate:
                if (isinstance(part,str)):
                    continue

                origBlendFile = None
                try:
                    origBlendFile = FileService.parseOSPath(part['filename'])
                except KeyError:
                    continue

                fixedBlendPath = self.getFixedBlendFile(origBlendFile)
                origBlendPaths[partIndex] = origBlendFile
                fixedBlendPaths[partIndex] = fixedBlendPath

                partIndex += 1

            remapBlendModel = RemapBlendModel(folderPath, fixedBlendName, fixedBlendPaths, origBlendName = resourceKey, origBlendPaths = origBlendPaths)
            self.remapBlendModelsDict[resourceKey] = remapBlendModel

        self.remapBlendModels = list(self.remapBlendModelsDict.values())

        # sort the resources
        self.remapBlendModels.sort(key = lambda model: self._getResourceSortKey((model.origBlendName, None)))

    def _getBlendResources(self, sectionName: str, blendResources: Set[str], subCommands: Set[str], subCommandLst: List[str]):
        ifTemplate = None
        
        try:
            ifTemplate = self._sectionIfTemplates[sectionName]
        except BaseException as e:
            raise KeyError(f"The section by the name '{sectionName}' does not exist") from e
        
        currentSubCommands = set()

        for part in ifTemplate:
            if (isinstance(part, str)):
                continue

            if (self._isIfTemplateResource(part)):
                resource = self._getIfTemplateResourceName(part)
                blendResources.add(resource)

            if (not self._isIfTemplateSubCommand(part)):
                continue
        
        # get all the unvisited subcommand sections to visit
        for partIndex in ifTemplate.calledSubCommands:
            subCommand = ifTemplate.calledSubCommands[partIndex]
            if (subCommand not in subCommands):
                currentSubCommands.add(subCommand)
                subCommands.add(subCommand)
                subCommandLst.append(subCommand)

        # get the blend resources from other subcommands
        for sectionName in currentSubCommands:
            self._getBlendResources(sectionName, blendResources, subCommands, subCommandLst)

    # parse(): Parses the merged.ini file for any info needing to keep track of
    def parse(self):
        self._sectionIfTemplates = self.getSectionOptions(self._sectionPattern, postProcessor = self._processIfTemplate)
        try:
            self._sectionIfTemplates[self._textureOverrideBlendRoot]
        except:
            return

        self._isRaidenIni = True
        blendResources = set()
        subCommands = { self._textureOverrideBlendRoot }
        subCommandLst = [self._textureOverrideBlendRoot]

        # keep track of all the needed blend dependencies
        self._getBlendResources(self._textureOverrideBlendRoot, blendResources, subCommands, subCommandLst)

        # read in all the needed dependencies
        for blend in blendResources:
            try:
                self._resourceBlends[blend] = self._sectionIfTemplates[blend]
            except BaseException as e:
                raise KeyError(f"The resource by the name, '{blend}', does not exist") from e

        for subCommand in subCommands:
            self._blendCommands[subCommand] = self._sectionIfTemplates[subCommand]
            self._blendCommandsRemapNames[subCommand] = self.getRemapName(subCommand)

        self._blendCommandsTuples = map(lambda subCommand: (subCommand, self._blendCommands[subCommand]), subCommandLst)
        self._makeRemapModels()


    def fix(self, keepBackup: bool = True, fixOnly: bool = False):
        fix = ""
        fix += self.getFixStr(fix = fix)
        self.injectAddition(f"\n\n{fix}", beforeOriginal = False, keepBackup = keepBackup, fixOnly = fixOnly)


class Mod(Model):
    def __init__(self, path: str = DefaultPath, files: Optional[List[str]] = None, logger: Optional[Logger] = None):
        super().__init__(logger = logger)
        self.path = path
        self._files = files
        self._setupFiles()

        self.inis, self.remapBlend, self.backupInis, self.backupDups = self.getOptionalFiles()
        self.inis = list(map(lambda iniPath: IniFile(iniPath, logger = logger), self.inis))

    @property
    def files(self):
        return self._files

    @files.setter
    def files(self, newFiles: Optional[List[str]] = None):
        self._files = newFiles
        self._setupFiles()

    def _setupFiles(self):
        if (self._files is None):
            self._files = FileService.getFiles(path = self.path)

    @classmethod
    def isIni(cls, file: str) -> bool:
        return file.endswith(IniExt)
    
    @classmethod
    def isRemapBlend(cls, file: str) -> bool:
        baseName = os.path.basename(file)
        if (not baseName.endswith(BufExt)):
            return False

        baseName = baseName.rsplit(".", 1)[0]
        baseNameParts = baseName.rsplit("RemapBlend", 1)

        return (len(baseNameParts) > 1)
    
    @classmethod
    def isBlend(cls, file: str) -> bool:
        return bool(file.endswith(BlendFileType) and not cls.isRemapBlend(file))
    
    @classmethod
    def isBackupIni(cls, file: str) -> bool:
        return BackupFilePrefix in file and file.endswith(TxtExt)
    
    @classmethod
    def isBackupDupFile(cls, file: str) -> bool:
        return DuplicateFilePrefix in file and file.endswith(TxtExt)
    
    def getBaseModFiles(self) -> List[str]:
        filters = {IniFileType: self.isIni}
        return FileService.getSingleFiles(path = self.path, filters = filters, files = self._files)
    
    def getOptionalFiles(self) -> List[Optional[str]]:
        SingleFileFilters = {}
        MultiFileFilters = [self.isIni, self.isRemapBlend, self.isBackupIni, self.isBackupDupFile]

        singleFiles = []
        if (SingleFileFilters):
            singleFiles = FileService.getSingleFiles(path = self.path, filters = SingleFileFilters, files = self._files, optional = True)
        multiFiles = FileService.getFiles(path = self.path, filters = MultiFileFilters, files = self._files)

        result = singleFiles
        if (not isinstance(result, list)):
            result = [result]

        result += multiFiles
        return result
    
    def removeBackupInis(self):
        for file in self.backupInis:
            self.print("log", f"Removing the backup ini, {os.path.basename(file)}")
            os.remove(file)

    def removeBackupDups(self):
        for file in self.backupDups:
            self.print("log", f"Removing the unused duplicate file, {os.path.basename(file)}")
            os.remove(file)

    def removeFix(self, fixedBlends: Set[str], fixedInis: Set[str], keepBackups: bool = True, fixOnly: bool = False):
        if (self.remapBlend is not None):
            for remapBlend in self.remapBlend:
                remapBlendFullPath = FileService.absPathOfRelPath(remapBlend, self.path)

                # remove only remap blends that have not been recently created
                if (remapBlendFullPath not in fixedBlends):
                    self.print("log", f"Removing previous {RemapBlendFile} at {os.path.basename(remapBlend)}")
                    os.remove(remapBlend)

        for ini in self.inis:
            iniFullPath = FileService.absPathOfRelPath(ini.file, self.path)
            if (iniFullPath not in fixedInis and ini.isRaidenIni):
                ini.removeFix(keepBackups = keepBackups, fixOnly = fixOnly)

    # correcting the blend file
    @classmethod
    def blendCorrection(self, blendFile: str, fixedBlendFile: str) -> str:
        with open(blendFile, "rb") as f:
            blendData = f.read()

        if len(blendData)%32 != 0:
            raise BlendFileNotRecognized(blendFile)

        result = bytearray()
        for i in range(0,len(blendData),32):
            blendweights = [struct.unpack("<f", blendData[i+4*j:i+4*(j+1)])[0] for j in range(4)]
            blendindices = [struct.unpack("<I", blendData[i+16+4*j:i+16+4*(j+1)])[0] for j in range(4)]
            outputweights = bytearray()
            outputindices = bytearray()
            for weight, index in zip(blendweights, blendindices):
                if weight != 0 and index <= MaxVGIndex:
                    index = int(VGRemap[str(index)])
                outputweights += struct.pack("<f", weight)
                outputindices += struct.pack("<I", index)
            result += outputweights
            result += outputindices

        with open(fixedBlendFile, "wb") as f:
            f.write(result)

        return fixedBlendFile
    
    def correctBlend(self, fixedRemapBlends: Dict[str, RemapBlendModel]):
        blendsFound = 0
        blendsSkipped = {}
        blendsFixed = set()

        for ini in self.inis:
            if (ini is None):
                continue

            for model in ini.remapBlendModels:
                for partIndex in model.fullPaths:
                    fixedFullPath = model.fullPaths[partIndex]
                    origFullPath = model.origFullPaths[partIndex]
                    blendFixed = True

                    try:
                        fixedRemapBlends[fixedFullPath]
                    except:
                        blendFixed = False
                    else:
                        self.print("log", f"Blend file has already been corrected at {fixedFullPath}")

                    if (blendFixed):
                        continue
                    
                    blendsFound += 1
                    try:
                        self.blendCorrection(origFullPath, fixedFullPath)
                    except BaseException as e:
                        blendsSkipped[fixedFullPath] = e 
                        self.print("handleException", e)
                    else:
                        self.print("log", f'Blend file correction done at {fixedFullPath}')
                        blendsFixed.add(fixedFullPath)
                        fixedRemapBlends[fixedFullPath] = model

        return [blendsFound, blendsFixed, blendsSkipped]


class RaidenBossFixService():
    def __init__(self, path: Optional[str] = None, keepBackups: bool = True, fixOnly: bool = False, undoOnly: bool = False, 
                 readAllInis: bool = False, log: bool = False, verbose: bool = True, handleExceptions: bool = False):
        self.log = log
        self._loggerBasePrefix = ""
        self.logger = Logger(logTxt = log, verbose = verbose)
        self._path = path
        self.keepBackups = keepBackups
        self.fixOnly = fixOnly
        self.undoOnly = undoOnly
        self.readAllInis = readAllInis
        self.verbose = verbose
        self.handleExceptions = handleExceptions
        self._logFile = FileService.parseOSPath(ntpath.join(DefaultPath, LogFile))
        self._pathIsCwd = False

        # certain statistics about the fix
        self.modsFound = 0
        self._skippedMods: Dict[str, BaseException] = {}
        self.blendsFound = 0
        self.blendsFixed = set()
        self.skippedBlends: Dict[str, Dict[str, BaseException]] = {}
        self.skippedBlendsCount = 0
        self.inisFound = 0
        self.inisFixed = set()

        self._setupModPath()

    @property
    def pathIsCwd(self):
        return self._pathIsCwd
    
    @property
    def path(self):
        return self._path
    
    @path.setter
    def path(self, newPath: str):
        self._path = newPath
        self._setupModPath()
        self._skippedMods = {}
    
    def _setupModPath(self):
        self._pathIsCwd = False
        if (self._path is None):
            self._path = DefaultPath
            self._pathIsCwd = True
            return

        self._path = FileService.parseOSPath(self._path)
        self._path = os.path.abspath(self._path)
        self._pathIsCwd = (self._path == DefaultPath)

    def getFixedBlendFile(self, blendFile: str) -> str:
        return f"{blendFile.split('Blend.buf')[0]}RemapBlend.buf"
    
    # fixes an ini file in a mod
    def fixIni(self, ini: IniFile, mod: Mod, fixedRemapBlends: Dict[str, RemapBlendModel]):
        # check if the .ini is for a raiden mod
        if (ini is None or not ini.isRaidenIni):
            return False

        if (self.undoOnly):
            return True

        # parse the .ini file
        ini.parse()
        if (ini.isRaidenFixed):
            self.logger.log(f"the ini file, {os.path.basename(ini.file)}, is already fixed")
            return False

        # fix the blends
        currentBlendsFound, currentBlendsFixed, currentBlendsSkipped = mod.correctBlend(fixedRemapBlends = fixedRemapBlends)
        self.blendsFound += currentBlendsFound
        self.blendsFixed = self.blendsFixed.union(currentBlendsFixed)

        if (currentBlendsSkipped):
            self.skippedBlends[mod.path] = currentBlendsSkipped
        self.skippedBlendsCount += len(currentBlendsSkipped)

        # writing the fixed file
        self.logger.log(f"Making the fixed ini file for {os.path.basename(ini.file)}")
        ini.fix(keepBackup = self.keepBackups, fixOnly = self.fixOnly)

        return True

    # fixes a mod
    def fixMod(self, mod: Mod, fixedRemapBlends: Dict[str, RemapBlendModel]) -> bool:
        # remove any backups
        if (not self.keepBackups):
            mod.removeBackupInis()

        for ini in mod.inis:
            ini.checkRaidenIni(isRaidenIni = self.readAllInis)

        # undo any previous fixes
        if (not self.fixOnly):
            mod.removeFix(self.blendsFixed, self.inisFixed, keepBackups = self.keepBackups)

        result = False
        inisLen = len(mod.inis)

        for i in range(inisLen):
            ini = mod.inis[i]
            iniIsFixed = self.fixIni(ini, mod, fixedRemapBlends)
            result = (result or iniIsFixed)

            if (not iniIsFixed):
                continue
            
            if (i < inisLen - 1):
                self.logger.space()
            iniFullPath = FileService.absPathOfRelPath(ini.file, mod.path)
            self.inisFixed.add(iniFullPath)
        
        return result
    
    def addTips(self):
        self.logger.includePrefix = False

        if (not self.undoOnly or self.keepBackups):
            self.logger.split()
            self.logger.openHeading("Tips", sideLen = 10)

            if (self.keepBackups):
                self.logger.bulletPoint(f'Hate deleting the "{BackupFilePrefix}" {IniExt}/{TxtExt} files yourself after running this script? (cuz I know I do!) Run this script again (on CMD) using the {DeleteBackupOpt} option')

            if (not self.undoOnly):
                self.logger.bulletPoint(f"Want to undo this script's fix? Run this script again (on CMD) using the {RevertOpt} option")

            if (not self.readAllInis):
                self.logger.bulletPoint(f"Were your {IniFileType}s not read because it does not contain the section named [TextureOverrideRaidenShogunBlend]? Run this script again (on CMD) using the {AllOpt} option")

            self.logger.space()
            self.logger.log("For more info on command options, run this script (on CMD) using the --help option")
            self.logger.closeHeading()

        self.logger.includePrefix = True


    def reportSkippedAsset(self, assetName: str, assetDict: Dict[str, BaseException], warnStrFunc: Callable[[str], str]):
        if (assetDict):
            message = f"WARNING: The following {assetName} were skipped due to warnings (see log above):\n\n"
            for dir in assetDict:
                message += warnStrFunc(dir)

            self.logger.error(message)
            self.logger.space()

    def warnSkippedBlends(self, modPath: str):
        relModPath = FileService.getRelPath(modPath, self._path)
        message = f"Mod: {relModPath}\n"
        blendWarnings = self.skippedBlends[modPath]
        
        for blendPath in blendWarnings:
            relBlendPath = FileService.getRelPath(blendPath, self._path)
            message += self.logger.getBulletStr(f"{relBlendPath} >>> {blendWarnings[blendPath]}\n")
        
        message += "\n"
        return message

    def reportSkippedMods(self):
        self.reportSkippedAsset("mods", self._skippedMods, lambda dir: self.logger.getBulletStr(f"{dir} >>> {self._skippedMods[dir]}\n"))
        self.reportSkippedAsset(f"{BlendFileType} files", self.skippedBlends, lambda dir: self.warnSkippedBlends(dir))

    def reportSummary(self):
        skippedMods = len(self._skippedMods)
        fixedMods = self.modsFound - skippedMods
        skippedBlends = len(self.skippedBlends)
        fixedBlends = self.blendsFound - skippedBlends
        fixedInis = len(self.inisFixed)
        skippedInis = self.inisFound - fixedInis

        self.logger.openHeading("Summary", sideLen = 10)
        self.logger.space()
        
        modFixMsg = ""
        blendFixMsg = ""
        iniFixMsg = ""
        if (not self.undoOnly):
            modFixMsg = f"Out of {self.modsFound} found mods, fixed {fixedMods} mods and skipped {skippedMods} mods"
            iniFixMsg = f"Out of the {self.inisFound} {IniFileType}s within the found mods, fixed {fixedInis} {IniFileType}s and skipped {skippedInis} {IniFileType} files"
            blendFixMsg = f"Out of the {self.blendsFound} {BlendFileType} files within the found mods, fixed {fixedBlends} {BlendFileType} files and skipped {skippedBlends} {BlendFileType} files"
        else:
            modFixMsg = f"Out of {self.modsFound} found mods, remove fix from {fixedMods} mods and skipped {skippedMods} mods"

        self.logger.bulletPoint(modFixMsg)
        if (iniFixMsg):
            self.logger.bulletPoint(iniFixMsg)

        if (blendFixMsg):
            self.logger.bulletPoint(blendFixMsg)

        self.logger.space()
        self.logger.closeHeading()

    def createLog(self):
        if (not self.log):
            return

        self.logger.includePrefix = False
        self.logger.space()

        self.logger.verbose = True
        self.logger.log(f"Creating log file, {LogFile}")

        self.logger.includePrefix = True
        self.logger.verbose = self.verbose

        with open(self._logFile, "w", encoding = IniFileEncoding) as f:
            f.write(self.logger.loggedTxt)

    def createMod(self, path: str = DefaultPath, files: Optional[List[str]] = None):
        mod = Mod(path = path, files = files, logger = self.logger)
        return mod

    def _fix(self):
        if (self.fixOnly and self.undoOnly):
            raise ConflictingOptions([FixOnlyOpt, RevertOpt])

        parentFolder = os.path.dirname(self._path)
        self._loggerBasePrefix = os.path.basename(self._path)
        self.logger.prefix = os.path.basename(DefaultPath)

        visitedDirs = set()
        visitingDirs = set()
        dirs = deque()
        dirs.append(self._path)
        visitingDirs.add(self._path)
        fixedRemapBlends = {}
    
        while (dirs):
            path = dirs.popleft()
            fixedMod = False

            # skip if the directory has already been visited
            if (path in visitedDirs):
                visitingDirs.remove(path)
                visitedDirs.add(path)
                continue 
            
            self.logger.split()

            # get the relative path to where the program runs
            self.logger.prefix = FileService.getRelPath(path, parentFolder)

            # try to make the mod, skip if cannot be made
            try:
                mod = self.createMod(path = path)
            except:
                visitingDirs.remove(path)
                visitedDirs.add(path)
                continue

            # fix the mod
            try:
                fixedMod = self.fixMod(mod, fixedRemapBlends)
            except BaseException as e:
                self.logger.handleException(e)
                if (mod.inis):
                    self._skippedMods[path] = e

            # get all the folders that could potentially be other mods
            modFiles, modDirs = FileService.getFilesAndDirs(path = path, recursive = True)

            if (mod.inis):
                for ini in mod.inis:
                    for blendModel in ini.remapBlendModels:
                        resourceModDirs = map(lambda partIndex: os.path.dirname(blendModel.origFullPaths[partIndex]), blendModel.origFullPaths) 
                        modDirs += resourceModDirs
            
            # add in all the folders that need to be visited
            for dir in modDirs:
                if (dir in visitedDirs):
                    continue

                if (dir not in visitingDirs):
                    dirs.append(dir)
                visitingDirs.add(dir)

            # increment the count of mods found
            if (fixedMod):
                self.inisFound += len(mod.inis)
                self.modsFound += 1

            visitingDirs.remove(path)
            visitedDirs.add(path)

        self.logger.split()
        self.logger.prefix = self._loggerBasePrefix
        self.reportSkippedMods()
        self.logger.space()
        self.reportSummary()


    def fix(self):
        try:
            self._fix()
        except BaseException as e:
            if (self.handleExceptions):
                self.logger.handleException(e)
            else:
                self.createLog()
                raise e from e
        else:
            noErrors = bool(not self._skippedMods and not self.skippedBlends)

            if (noErrors):
                self.logger.space()
                self.logger.log("ENJOY")

            self.logger.split()

            if (noErrors):
                self.addTips()

        self.createLog()


def main():
    args = argParser.parse_args()
    raidenBossFixService = RaidenBossFixService(path = args.src, keepBackups = not args.deleteBackup, fixOnly = args.fixOnly, 
                                                undoOnly = args.revert, readAllInis = args.all, 
                                                log = args.log, verbose = True, handleExceptions = True)
    raidenBossFixService.fix()
    raidenBossFixService.logger.waitExit()

# Main Driver Code
if __name__ == "__main__":
    main()