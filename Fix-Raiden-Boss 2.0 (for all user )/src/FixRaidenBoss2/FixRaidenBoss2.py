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
from typing import List, Callable, Optional, Union, Dict, Any, TypeVar, Hashable, Tuple
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
IniExtLen = len(IniExt)
MergedFile = f"merged{IniExt}"
BackupFilePrefix = "DISABLED_RSFixBackup_"
DuplicateFilePrefix = "DISABLED_RSDup_"
LogFile = f"RSFixLog{TxtExt}"

IniFileType = "*.ini file"
BlendFileType = "Blend.buf"
RemapBlendFile = f"RaidenShogunRemap{BlendFileType}"
IniFileEncoding = "utf-8"

DeleteBackupOpt = '--deleteBackup'
FixOnlyOpt = '--fixOnly'
RevertOpt = '--revert'
PurgeDupsOpt = '--purgeDups'
argParser = argparse.ArgumentParser(description='Fixes Raiden Boss Phase 1 for all types of mods', formatter_class=argparse.MetavarTypeHelpFormatter)
argParser.add_argument('-s', '--src', action='store', type=str, help="The path to the Raiden mod folder. If this option is not specified, then will use the current directory as the mod folder.")
argParser.add_argument('-d', DeleteBackupOpt, action='store_true', help=f'deletes backup copies of the original {IniExt} files')
argParser.add_argument('-f', FixOnlyOpt, action='store_true', help='only fixes the mod without cleaning any previous runs of the script')
argParser.add_argument('-r', RevertOpt, action='store_true', help='reverts back previous runs of the script')
argParser.add_argument('-m', '--manualDisable', action='store_true', help=f'goes into an error when duplicate {IniExt} or {BlendFileType} are found in a mod instead of choosing which file you want to use')
argParser.add_argument('-p', PurgeDupsOpt, action='store_true', help=f'deletes unused duplicate {IniExt} or {BlendFileType} instead of keeping a disabled backup copy of those files')
argParser.add_argument('-l', '--log', action='store_true', help=f'Logs the printed out log into a seperate {TxtExt} file')

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
    

class ListTools():
    @classmethod
    def to_dict(cls, lst: List[T], get_id: Callable[[T], Hashable]) -> Dict[Hashable, T]:
        return {get_id(e): e for e in lst}


class FileService():
    @classmethod
    def getFilesAndDirs(cls, path: str = DefaultPath) -> List[List[str]]:
        files = []
        dirs = []

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


class Logger():
    DefaultHeadingSideLen = 2
    DefaultHeadingChar = "="

    def __init__(self, prefix: str = "", logTxt: bool = False, verbose: bool = True):
        self.prefix = prefix
        self._headingTxtLen = 0
        self._headingSideLen = 0
        self._headingChar = ""
        self.includePrefix = True
        self.verbose = verbose
        self.logTxt = logTxt
        self._loggedTxt = ""

        self._setDefaultHeadingAtts()

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
        return f"# {self.prefix} --> {message}"

    def log(self, message: str):
        if (not self.verbose):
            return

        if (self.includePrefix):
            message = self.getStr(message)

        self._addLogTxt(message)
        print(message)

    def split(self):
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
    def __init__(self, fixedBlendName: str, draw: str, path: str, origBlendName: Optional[str] = None):
        self.fixedBlendName = fixedBlendName
        self.draw = draw
        self.path = path
        self.blendPath = os.path.join(self.path, f"{self.fixedBlendName}.buf")
        self.origBlendName = origBlendName


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

    Vb1 = "vb1"
    Draw = "draw"
    Resource = "Resource"
    Blend = "Blend"
    RemapBlend = f"Remap{Blend}"

    # -- regex strings ---
    _textureOverrideBlendPatternStr = r"\[\s*TextureOverride(\w+)" + Blend + r"\s*\]"
    _commandListBlendPatternStr = r"\[\s*CommandListRaidenShogun" + Blend + r"\s*\]"
    _resourceBlendPatternStr = r"\[\s*" + Resource + r"((?!RaidenShogunRemap).)*" + Blend + r"\.[0-9]+\s*\]"

    _fixedTextureOverrideBlendPatternStr = r"\[\s*TextureOverrideRaidenShogun" + RemapBlend + r"\s*\]"
    _fixedCommandListBlendPatternStr = r"\[\s*CommandListRaidenShogun" + RemapBlend + r"\s*\]"

    # --------------------

    # -- regex objects ---
    _textureOverrideBlendPattern = re.compile(_textureOverrideBlendPatternStr)
    _commandListBlendPattern = re.compile(_commandListBlendPatternStr)
    _resourceBlendPattern = re.compile(_resourceBlendPatternStr)

    _fixedTextureOverrideBlendPattern = re.compile(_fixedTextureOverrideBlendPatternStr)
    _fixRemovalPattern = re.compile(f"{_fixHeader}(.|\n)*{_fixFooter}")

    _numEndPattern = re.compile(f"\.[0-9]+\s*$")

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
        self._merged = self.isMerged()

        self._textureOverideBlendDicts: Dict[str, Dict[str, Any]] = {}
        self._resourceBlendDicts: Dict[str, Dict[str, Any]] = {}
        self._blendIfTemplate: List[Union[str, Dict[str, Any]]] = []
        self._hasblendIfTemplate = False

    @property
    def isRaidenFixed(self):
        return self._isRaidenFixed
    
    @property
    def merged(self):
        return self._merged
    
    @classmethod
    def checkMerged(cls, file: str) -> bool:
        return file.endswith(MergedFile)
    
    def isMerged(self) -> bool:
        return self.checkMerged(self.file)
    
    def clearRead(self):
        self._fileLines = []
        self._fileLinesRead = False
        self._isRaidenFixed = False

    def read(self) -> str:
        self._merged = self.isMerged()
        result = ""
        with open(self.file, "r", encoding = IniFileEncoding) as f:
            result = f.read()
        return result
    
    def write(self):
        txtToWrite = "".join(self._fileLines)
        with open(self.file, "w", encoding = IniFileEncoding) as f:
            f.write(txtToWrite)

    def getFileLines(self) -> List[str]:
        with open(self.file, "r", encoding = IniFileEncoding) as f:
            self._fileLines = f.readlines()

        self._fileLinesRead = True
        return self._fileLines

    def _readLines(func):
        def readLinesWrapper(self, *args, **kwargs):
            if (not self._fileLinesRead):
                self.getFileLines()
            return func(self, *args, **kwargs)
        return readLinesWrapper

    def _checkRaidenFixed(self, line: str):
        if (not self._isRaidenFixed and self._fixedTextureOverrideBlendPattern.match(line)):
            self._isRaidenFixed = True

    def _parseSection(self, sectionName: str, srcTxt: str, save: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        self._parser.read_string(srcTxt)
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
                result[currentSectionName] = postProcessor(currentSectionStartInd, i, self._fileLines, currentSectionName, currentSectionToParse)

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

    def _processIfTemplate(self, startInd: int, endInd: int, fileLines: List[str], sectionName: str, srcTxt: str) -> List[Union[str, int]]:
        ifTemplate = []
        dummySectionName = "dummySection"
        currentDummySectionName = f"{dummySectionName}"
        replaceSection = ""
        atReplaceSection = False

        for i in range(startInd + 1, endInd):
            line = fileLines[i]
            isConditional = bool(self._ifStructurePattern.match(line))

            if (isConditional and not self._hasblendIfTemplate):
                self._hasblendIfTemplate = True

            if (isConditional and atReplaceSection):
                currentDummySectionName = f"{dummySectionName}{i}"
                replaceSection = f"[{currentDummySectionName}]\n{replaceSection}"
                ifTemplate.append(self._parseSection(currentDummySectionName, replaceSection))
                replaceSection = ""

            if (isConditional):
                ifTemplate.append(line)
                atReplaceSection = False
                continue
            
            replaceSection += line
            atReplaceSection = True

        # get any remainder replacements in the if..else template
        if (replaceSection != ""):
            currentDummySectionName = f"{dummySectionName}END"
            replaceSection = f"[{currentDummySectionName}]\n{replaceSection}"
            result = self._parseSection(currentDummySectionName, replaceSection)
            ifTemplate.append(result)

        self._blendIfTemplate = ifTemplate
        return ifTemplate

    def _processTextureOverideBlendSection(self, startInd: int, endInd: int, fileLines: List[str], sectionName: str, srcTxt: str) -> Dict[str, str]:
        return self._parseSection(sectionName, srcTxt, save = self._textureOverideBlendDicts)
    
    def _processResourceBlendSection(self, startInd: int, endInd: int, fileLines: List[str], sectionName: str, srcTxt: str) -> Dict[str, str]:
        return self._parseSection(sectionName, srcTxt, save = self._resourceBlendDicts)

    def getTextureOverideBlendDicts(self) -> Dict[str, Dict[str, Any]]:
        return self.getSectionOptions(self._textureOverrideBlendPattern, postProcessor = self._processTextureOverideBlendSection)
    
    def getResourceBlendDicts(self) -> Dict[str, Dict[str, Any]]:
        return self.getSectionOptions(self._resourceBlendPattern, postProcessor = self._processResourceBlendSection)

    # get the needed draw value
    def getBlendDrawValue(self, textureOverideKvps: Optional[Dict[str, Any]] = None) -> Optional[str]:
        if (textureOverideKvps is None and self._textureOverideBlendDicts):
            textureOverideKvps = DictTools.getFirstValue(self._textureOverideBlendDicts)

        if textureOverideKvps[self.Draw]:
            draw: str = textureOverideKvps[self.Draw]
        return draw
    
    @classmethod
    def getSectionRegexStr(cls, sectionName: str) -> str:
        return r"\[\s*" + sectionName + r"\s*\]"
    
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
            resourceDicts = self._resourceBlendDicts

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
    def getTextureOverride(self, fixedBlendName: str) -> str:
        return f"[TextureOverride{fixedBlendName}]\nhash = fe5c0180"
    
    @classmethod
    def getCommandName(self, name: str) -> str:
        return f"CommandList{name}"
    
    @classmethod
    def getResourceName(self, name: str) -> str:
        return f"{self.Resource}{name}"

    @classmethod
    def getRemapResourceName(cls, name: str) -> str:
        nameParts = name.rsplit(cls.Blend, 1)
        namePartsLen = len(nameParts)

        if (namePartsLen > 1):
            name = cls.RemapBlend.join(nameParts)
        else:
            name += cls.RemapBlend
        
        if (not name.startswith(cls.Resource)):
            name = cls.getResourceName(name)

        return name
    
    @classmethod
    def getResource(self, resourceName: str, filePath: str):
        return f"[{resourceName}]\ntype = Buffer\nstride = 32\nfilename = {filePath}"
    
    # creates the resource sections for the blends
    @classmethod
    def getResources(cls, remapBlendModels: List[RemapBlendModel]) -> str:
        result = ""

        remapBlendModelsLen = len(remapBlendModels)
        for i in range(remapBlendModelsLen):
            model = remapBlendModels[i]
            resourceName = cls.getRemapResourceName(model.origBlendName)

            if (i):
                result += "\n\n"

            result += cls.getResource(resourceName, model.blendPath)

        return result
    
    @classmethod
    def getFixMapping(cls, blendName: str, draw: int, tabCount: int = 1) -> str:
        tabs = "\t" * tabCount
        return f"{tabs}{cls.Vb1} = {blendName}\n{tabs}handling = skip\n{tabs}{cls.Draw} = {draw}"

    def _isIfTemplateResource(self, ifTemplateClauseDict: Dict[str, Any]) -> bool:
        return self.Vb1 in ifTemplateClauseDict
    
    def _getIfTemplateResourceName(self, ifTemplateClauseDict: Dict[str, Any]) -> Any:
        return ifTemplateClauseDict[self.Vb1]

    # fills the if..else template in merged.ini to create the command that maps created blend files to their
    #   corresponding mod
    def fillRemapCommandIfTemplate(self, commandName: str, remapBlendModelsDict: Dict[str, RemapBlendModel]):
        addFix = f"[{commandName}]\n"
        tabCount = 0

        for line in self._blendIfTemplate:
            if (isinstance(line, str)):
                addFix += line
                
                linePrefix = re.match(r"^[\t]*[^\s]*", line)

                if (linePrefix):
                    linePrefix = linePrefix.group(0)
                    tabCount = linePrefix.count("\t")

                    if (linePrefix.find("endif") == -1):
                        tabCount += 1
                continue

            if (self._isIfTemplateResource(line)):
                blendName = self._getIfTemplateResourceName(line)
                resourceBlendName = self.getRemapResourceName(blendName)

                remapModel = None
                try:
                    remapModel = remapBlendModelsDict[blendName]
                except KeyError as e:
                    raise KeyError(f'The blend resource by the name, "{blendName}", does not exist') from e

                addFix += f"{self.getFixMapping(resourceBlendName, remapModel.draw, tabCount = tabCount)}\n"
            
        return addFix
    
    # creates the command in merged.ini that maps the created blend files to their corresponding mod
    @classmethod
    def getRemapCommand(cls, commandName: str, remapBlendModels: List[RemapBlendModel]):
        addFix = f"[{commandName}]"

        remapBlendModelsLen = len(remapBlendModels)
        for i in range(remapBlendModelsLen):
            model = remapBlendModels[i]

            addFix += "\n"
            if (i):
                addFix += "else "

            blendName = f"{cls.getRemapResourceName(model.origBlendName)}"
            addFix += f"if $swapvar == {i}\n{cls.getFixMapping(blendName, model.draw)}"

        addFix += "\nendif"
        return addFix

    # get the needed lines to fix the .ini file
    @_addFixBoilerPlate
    def getFixStr(self, fix: str) -> str:
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
        pass

    @_readLines
    def removeFix(self, keepBackups: bool = True, fixOnly: bool = False):
        if (keepBackups and not fixOnly):
            self.print("log", f"Creating Backup for {os.path.basename(self.file)}")
            self.disIni()

        self.print("log", f"Removing any previous changes from this script in {os.path.basename(self.file)}")
        self._removeFix()

    def processSection(self, startInd: int, endInd: int, fileLines: List[str], sectionName: str, srcTxt: str):
        pass

    def parse(self):
        pass

    def fix(self, remapBlendModels: Union[RemapBlendModel, List[RemapBlendModel]], keepBackup: bool = True, fixOnly: bool = False):
        pass


class BaseIniFile(IniFile):
    _fixedResourceBlendPatternStr = r"\[\s*ResourceRaidenShogunRemapBlend.*\]"

    _removalPattern = re.compile(f"({IniFile._fixedTextureOverrideBlendPatternStr})|({_fixedResourceBlendPatternStr})")
    _parsePattern = re.compile(f"({IniFile._textureOverrideBlendPatternStr})")

    # get the needed lines to add to the each individual *.ini file
    def getFixStr(self, fixedBlendName: str, draw: str) -> str:
        resourceName = self.getResourceName(fixedBlendName)

        addFix = f"\n\n{self.getTextureOverride(fixedBlendName)}\n{IniFile.Vb1} = {self.getResourceName(fixedBlendName)}\nhandling = skip\n{IniFile.Draw} = {draw}"
        addFix += f'\n\n{self.getResource(resourceName, f"{fixedBlendName}.buf")}'

        return super().getFixStr(addFix)

    def _removeFix(self):
        self._removeScriptFix()
        self.getFileLines()
        self.removeSectionOptions(self._removalPattern)
        self.write()
        self.clearRead()

    def processSection(self, startInd: int, endInd: int, fileLines: List[str], sectionName: str, srcTxt: str) -> Dict[str, str]:
        return self._processTextureOverideBlendSection(startInd, endInd, fileLines, sectionName, srcTxt)

    def parse(self):
        self.getSectionOptions(self._parsePattern, postProcessor = self.processSection)

    def fix(self, remapBlendModel: RemapBlendModel, keepBackup: bool = True, fixOnly: bool = False):
        addFix = self.getFixStr(remapBlendModel.fixedBlendName, remapBlendModel.draw)
        self.injectAddition(addFix, keepBackup = keepBackup, fixOnly = fixOnly)


class MergedIniFile(IniFile):
    _fixedResourceBlendPatternStr = r"\[\s*ResourceRaidenShogunRemapBlend.*\]"
    _removalPattern = re.compile(f"({IniFile._fixedTextureOverrideBlendPatternStr})|({IniFile._fixedCommandListBlendPatternStr})|({_fixedResourceBlendPatternStr})")

    def __init__(self, file: str, logger: Optional[Logger] = None):
        super().__init__(file, logger = logger)
        self.blendDrawValues: Dict[str, int] = {}

    # get the needed lines to add to the merged.ini file
    def getFixStr(self, globalBlendName: str, remapBlendModels: List[RemapBlendModel], remapBlendModelsDict: Dict[str, RemapBlendModel]) -> str:
        commandName = self.getCommandName(globalBlendName)
        remapBlendCommand = ""

        if (self._hasblendIfTemplate):
            self.print("log", "Filling if..else template in mapping function")
            remapBlendCommand = self.fillRemapCommandIfTemplate(commandName, remapBlendModelsDict)
        else:
            self.print("log", "Creating mapping function")
            remapBlendCommand = self.getRemapCommand(commandName, remapBlendModels)

        addFix = f"\n\n{self.getTextureOverride(globalBlendName)}"
        addFix += f"\nrun = {commandName}"
        addFix += f"\n\n{remapBlendCommand}"
        addFix += f"\n\n{self.getResources(remapBlendModels)}"

        return super().getFixStr(addFix)
    
    def _removeFix(self):
        self._removeScriptFix()
        self.getFileLines()
        self.removeSectionOptions(self._removalPattern)
        self.write()
        self.clearRead()
    
    # parse(): Parses the merged.ini file for any info needing to keep track of
    # Note: We use 2 passes to parse the merged.ini file
    #   Pass 1: reads in the required dependencies from [CommandListRaidenShogunBlend]
    #   Pass 2: read the file locations of the required dependencies
    # Can't read in 1 pass (eg. case where [CommandListRaidenShogunBlend] comes after the resource dependencies in the .ini file)
    def parse(self):
        self.getSectionOptions(IniFile._commandListBlendPattern, postProcessor = self._processIfTemplate)

        nonStandardResourceBlends: Dict[str, str] = {}
        resourceBlendPatternStr = f"({IniFile._resourceBlendPatternStr})"

        # keep track of any info for needed dependencies that do not fit the naming convention from the mod merging script
        for line in self._blendIfTemplate:
            if (isinstance(line, str) or not self._isIfTemplateResource(line)):
                continue

            blendName = self._getIfTemplateResourceName(line)
            
            # retrive the draw values of a particular mod so we do not necessarily need to get the value from the
            #   mods's .ini file
            if (IniFile.Draw in line):
                self.blendDrawValues[blendName] = line[IniFile.Draw]

            if (IniFile._resourceBlendPattern.match(f"[{blendName}]") or blendName in nonStandardResourceBlends):
                continue

            resourceRegex = self.getSectionRegexStr(blendName)
            nonStandardResourceBlends[blendName] = resourceRegex
            resourceBlendPatternStr += f"|({resourceRegex})"

        # read in all the needed dependencies
        resouceBlendPattern = re.compile(resourceBlendPatternStr)
        self.getSectionOptions(resouceBlendPattern, postProcessor = self._processResourceBlendSection)

    def fix(self, remapBlendModels: List[RemapBlendModel], keepBackup: bool = True, fixOnly: bool = False):
        remapBlendModelsDict = ListTools.to_dict(remapBlendModels, lambda e: e.origBlendName)

        addFix = self.getFixStr(remapBlendModels[0].fixedBlendName, remapBlendModels, remapBlendModelsDict)
        self.injectAddition(f"\n\n{addFix}", beforeOriginal = False, keepBackup = keepBackup, fixOnly = fixOnly)


class Mod(Model):
    def __init__(self, path: str = DefaultPath, files: Optional[List[str]] = None, isTopMod: bool = False, logger: Optional[Logger] = None, blendDraw: Optional[str] = None):
        super().__init__(logger = logger)
        self.path = path
        self.isTopMod = isTopMod
        self._files = files
        self.blendDraw = blendDraw
        self._setupFiles()

        if (self.isTopMod):
            self.ini = self.getBaseModFiles()
            self.remapBlend, self.blend, self.backupInis, self.backupDups = self.getOptionalFiles()
        elif (self.blendDraw is None):
            self.ini, self.blend = self.getBaseModFiles()
            self.remapBlend, self.backupInis, self.backupDups = self.getOptionalFiles()
        else:
            self.blend = self.getBaseModFiles()
            self.remapBlend, self.ini, self.backupInis, self.backupDups = self.getOptionalFiles()

        hasIniFile = bool(self.ini is not None)
        if (hasIniFile and IniFile.checkMerged(self.ini)):
            self.ini = MergedIniFile(self.ini, logger = logger)
        elif (hasIniFile):
            self.ini = BaseIniFile(self.ini, logger = logger)

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
        return file.endswith(RemapBlendFile)
    
    @classmethod
    def isBlend(cls, file: str) -> bool:
        return bool(file.endswith(BlendFileType) and not cls.isRemapBlend(file))
    
    @classmethod
    def isBackupIni(cls, file: str) -> bool:
        return BackupFilePrefix in file and file.endswith(TxtExt)
    
    @classmethod
    def isBackupDupFile(cls, file: str) -> bool:
        return DuplicateFilePrefix in file and file.endswith(TxtExt)
    
    def getBlendDrawValue(self, flush: bool = False) -> str:
        if (flush and self.ini is not None):
            self.blendDraw = self.ini.getBlendDrawValue()
        return self.blendDraw
    
    def getBaseModFiles(self) -> List[str]:
        filters = {}
        if (self.blendDraw is None):
            filters[IniFileType] = self.isIni

        if (not self.isTopMod):
            filters[BlendFileType] =  self.isBlend

        return FileService.getSingleFiles(path = self.path, filters = filters, files = self._files)
    
    def getOptionalFiles(self) -> List[Optional[str]]:
        SingleFileFilters = {"Remap Blend": self.isRemapBlend}
        if (self.isTopMod):
            SingleFileFilters[BlendFileType] = self.isBlend
        elif (self.blendDraw is not None):
            SingleFileFilters[IniFileType] = self.isIni

        MultiFileFilters = [self.isBackupIni, self.isBackupDupFile]

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

    def removeFix(self, keepBackups: bool = True, fixOnly: bool = False):
        if (self.remapBlend is not None):
            self.print("log", f"Removing previous {RemapBlendFile}")
            os.remove(self.remapBlend)

        if (self.ini is not None):
            self.ini.removeFix(keepBackups = keepBackups, fixOnly = fixOnly)


class RaidenBossFixService():
    def __init__(self, path: Optional[str] = None, keepBackups: bool = True, fixOnly: bool = False, undoOnly: bool = False, 
                 disableDups: bool = False, purgeDups: bool = False, log: bool = False, verbose: bool = True, handleExceptions: bool = False):
        self.log = log
        self._loggerBasePrefix = ""
        self.logger = Logger(logTxt = log, verbose = verbose)
        self._path = path
        self.keepBackups = keepBackups
        self.fixOnly = fixOnly
        self.undoOnly = undoOnly
        self.disableDups = disableDups
        self.purgeDups = purgeDups
        self.verbose = verbose
        self.handleExceptions = handleExceptions
        self._skippedMods: Dict[str, Error] = {}
        self._logFile = FileService.parseOSPath(ntpath.join(DefaultPath, LogFile))
        self._pathIsCwd = False

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
        else:
            self._path = FileService.parseOSPath(self._path)

    def getFixedBlendFile(self, blendFile: str) -> str:
        return f"{blendFile.split('Blend.buf')[0]}RemapBlend.buf"

    # correcting the blend file
    def _blendCorrection(self, blendFile: str) -> str:
        self.logger.log("Correcting the blend file")

        with open(blendFile, "rb") as f:
            blendData = f.read()

        if len(blendData)%32 != 0:
            self.logger.log()
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
        fixedBlendFile = self.getFixedBlendFile(blendFile)
        with open(fixedBlendFile, "wb") as f:
            f.write(result)
        self.logger.log('Blend file correction done')
        return fixedBlendFile

    # fix each individual mod containing the assets
    def fixBaseMod(self, mod: Mod, origBlendName: Optional[str] = None) -> Optional[RemapBlendModel]:
        # remove any backups
        if (not self.keepBackups):
            mod.removeBackupInis()

        if (self.purgeDups):
            mod.removeBackupDups()

        # undo any previous fixes
        if (not self.fixOnly):
            mod.removeFix(keepBackups = self.keepBackups)

        if (self.undoOnly):
            return

        # parse the .ini file
        if (mod.ini is not None):
            mod.ini.parse()

        draw = mod.getBlendDrawValue(flush = True)
        fixedBlendName = self.getFixedBlendFile(mod.blend)
        fixedBlendName = os.path.basename(fixedBlendName).split('.')[0]

        remapBlendPath = ntpath.relpath(mod.path, self._path)
        remapBlendModel = RemapBlendModel(fixedBlendName, draw, remapBlendPath, origBlendName = origBlendName)
        self._blendCorrection(mod.blend)
        if (mod.ini is None):
            self.logger.note(f"No {IniFileType} for the mod was provided, so we use info provided by the {MergedFile}")
            return remapBlendModel
        
        if (mod.ini.isRaidenFixed):
            self.logger.log("ini file already fixed")
            return remapBlendModel

        # writing the fixed file
        self.logger.log("Making the fixed ini file")
        mod.ini.fix(remapBlendModel, keepBackup = self.keepBackups, fixOnly = self.fixOnly)
        return remapBlendModel
    
    def addTips(self):
        self.logger.includePrefix = False

        if (not self.undoOnly or self.keepBackups):
            self.logger.split()
            self.logger.openHeading("Tips", sideLen = 10)

            if (self.keepBackups):
                self.logger.bulletPoint(f'Hate deleting the "{BackupFilePrefix}" {IniExt}/{TxtExt} files yourself after running this script? (cuz I know I do!) Run this script again (on CMD) using the {DeleteBackupOpt} option')
            
            if (not self.purgeDups):
                self.logger.bulletPoint(f'Hate deleting the "{DuplicateFilePrefix}" {IniExt}/{TxtExt} files yourself after disabling the duplicate {IniExt}/{BlendFileType} files? Run this script again (on CMD) using the {PurgeDupsOpt} option')

            if (not self.undoOnly):
                self.logger.bulletPoint(f"Want to undo this script's fix? Run this script again (on CMD) using the {RevertOpt} option")

            self.logger.space()
            self.logger.log("For more info on command options, run this script (on CMD) using the --help option")
            self.logger.closeHeading()

        self.logger.includePrefix = True


    def reportSkippedMods(self):
        if (self._skippedMods):
            message = f"WARNING: The following mods were skipped due to warnings (see log above):\n\n"
            for dir in self._skippedMods:
                warnStr = self._skippedMods[dir].warn()
                message += self.logger.getBulletStr(f"{dir} >>> {warnStr}\n")

            self.logger.error(message)
            self.logger.space()

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


    def disableDuplicateFiles(self, fileType: str, files: List[str], folderPath: str):
        if (self.disableDups):
            filesLen = len(files)
            baseFiles = list(map(os.path.basename, files))
            baseFilesSet = set(baseFiles)

            self.logger.includePrefix = False
            
            self.logger.space()

            choiceStr = None
            validInput = False
            selected = None

            while (not validInput):
                if (choiceStr is not None):
                    self.logger.space()
                    self.logger.log("Invalid input")
                    self.logger.closeHeading()
                    self.logger.space()

                self.logger.openHeading(f"Duplicate {fileType} Detected")

                self.logger.space()
                self.logger.log(f"Choose which file you want to use for the mod at {folderPath}")

                self.logger.space()
                self.logger.list(baseFiles)

                self.logger.space()
                choiceStr = self.logger.input(f"[enter a number from 1-{filesLen} or enter the file name]:\n")

                try:
                    selected = int(choiceStr)
                except:
                    pass
                else:
                    if (selected >= 1 and selected <= filesLen):
                        validInput = True
                        break

                if (choiceStr in baseFilesSet):
                    selected = choiceStr
                    validInput = True

            if (isinstance(selected, int)):
                selected = baseFiles[selected - 1]

            self.logger.space()
            self.logger.log(f"Chosen file to use: {selected}")

            if (self.purgeDups):
                self.logger.log("Deleting all the other files")
            else:
                self.logger.log("Disabling all the other files")

            files = filter(lambda file: (os.path.basename(file) != selected), files)
            for file in files:
                if (self.purgeDups):
                    os.remove(file)
                    continue

                FileService.disableFile(file, filePrefix = DuplicateFilePrefix)

            self.logger.closeHeading()
            self.logger.space()
            self.logger.includePrefix = True

    def createMod(self, path: str = DefaultPath, files: Optional[List[str]] = None, isTopMod: bool = False, blendDraw: Optional[int] = None):
        if (not self.disableDups):
            return Mod(path = path, files = files, isTopMod = isTopMod, logger = self.logger, blendDraw = blendDraw)
        
        mod = None
        while (mod is None):
            try:
                mod = Mod(path = path, files = files, isTopMod = isTopMod, logger = self.logger, blendDraw = blendDraw)
            except DuplicateFileException as e:
                self.disableDuplicateFiles(e.fileType, e.files, path)

            if (mod is None):
                self.logger.space()
                self.logger.log("Retrying reading mod")
                files = None

        return mod

    def _fix(self):
        if (self.fixOnly and self.undoOnly):
            raise ConflictingOptions([FixOnlyOpt, RevertOpt])

        modFolder = os.path.basename(self._path)

        self._loggerBasePrefix = os.path.basename(modFolder)
        self.logger.prefix = os.path.basename(DefaultPath)
        files, dirs = FileService.getFilesAndDirs(path = self._path)

        self.logger.prefix = self._loggerBasePrefix
        topMod = self.createMod(path = self._path, files = files, isTopMod = True)
        topIni = topMod.ini

        if (topIni.merged):
            self.logger.log("Fixing Merged Mod")
            self.logger.log(f"Reading {MergedFile} file for individual mods to modify")

            # read the merged.ini for mod folders
            topIni.parse()
            modFolders = topIni.getResourceBlendFolderPaths()

            # remove any backups
            if (not self.keepBackups):
                topMod.removeBackupInis()

            if (self.purgeDups):
                topMod.removeBackupDups()

            # undo any previous fixes
            if (not self.fixOnly):
                topMod.removeFix(keepBackups = self.keepBackups)

            remapBlendModelsDict = {}
            remapBlendModels = []

            for resourceName in modFolders:
                dir = modFolders[resourceName]
                dirName = FileService.ntPathToPosix(dir)

                dirPath = dirName
                if (not self._pathIsCwd):
                    dirPath = FileService.parseOSPath(ntpath.join(self._path, dir))

                self.logger.split()
                self.logger.prefix = f"{self._loggerBasePrefix} --> {dirName.replace(os.sep, ' --> ')}"

                # case where a mod folder is called twice in merged.ini
                try:
                    remapBlendModelsDict[dirName]
                except:
                    pass
                else:
                    remapBlendModels.append(remapBlendModelsDict[dirName])
                    self.logger.log(f"Mod located at {dirName} has already been fixed")
                    continue

                mod = None
                modBlendDraw = None
                try:
                    modBlendDraw = topMod.ini.blendDrawValues[resourceName]
                except KeyError:
                    pass

                try:
                    mod = self.createMod(path = dirPath, blendDraw = modBlendDraw)
                except FileException as e:
                    self.logger.warn(e)
                    self.logger.space()
                    self.logger.log("Skipping mod...")
                    
                    self._skippedMods[dirName] = e
                    continue

                remapBlendModel = self.fixBaseMod(mod, origBlendName = resourceName)

                if (self.undoOnly):
                    continue

                remapBlendModels.append(remapBlendModel)
                remapBlendModelsDict[dirName] = remapBlendModel

            self.logger.split()
            self.logger.prefix = self._loggerBasePrefix 

            self.reportSkippedMods()

            if (self.undoOnly):
                self.logger.log("Finished reverting previous changes")
                return

            if (not remapBlendModels):
                self.logger.log("No mods found for the merged mod or all mods have already been converted")
                return

            if (topIni.isRaidenFixed):
                self.logger.log(f"{MergedFile} file already fixed")
                return

            self.logger.log(f"Making the {MergedFile} file")
            topIni.fix(remapBlendModels, keepBackup = self.keepBackups, fixOnly = self.fixOnly)
        else:
            self.logger.log("Fixing Single Mod")
            self.fixBaseMod(topMod)

        self.logger.log("ENJOY")

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
            self.logger.split()

            if (not self._skippedMods):
                self.addTips()

        self.createLog()


def main():
    args = argParser.parse_args()
    raidenBossFixService = RaidenBossFixService(path = args.src, keepBackups = not args.deleteBackup, fixOnly = args.fixOnly, 
                                                undoOnly = args.revert, disableDups = not args.manualDisable, purgeDups = args.purgeDups, 
                                                log = args.log, verbose = True, handleExceptions = True)
    raidenBossFixService.fix()
    raidenBossFixService.logger.waitExit()

# Main Driver Code
if __name__ == "__main__":
    main()