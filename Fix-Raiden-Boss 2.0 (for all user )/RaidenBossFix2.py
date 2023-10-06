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
from typing import List, Callable, Optional, Union, Dict, Any
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
os.chdir(os.path.dirname(os.path.abspath(__file__)))

DefaultFileType = "file"
DefaultPath = os.getcwd()
IniExt = ".ini"
TxtExt = ".txt"
IniExtLen = len(IniExt)
MergedFile = f"merged{IniExt}"
BackupFilePrefix = "DISABLED_RSFixBackup_"

IniFileType = "*.ini file"
BlendFileType = "Blend.buf"
RemapBlendFile = f"RaidenShogunRemap{BlendFileType}"
IniFileEncoding = "utf-8"

FixOnlyOpt = '--fixOnly'
RevertOpt = '--revert'
argParser = argparse.ArgumentParser(description='Fixes Raiden Boss')
argParser.add_argument('-d', '--deleteBackup', action='store_true', help='deletes backup copies of the original .ini files')
argParser.add_argument('-f', FixOnlyOpt, action='store_true', help='only fixes the mod without cleaning any previous runs of the script')
argParser.add_argument('-r', RevertOpt, action='store_true', help='reverts back previous runs of the script')


class Error(Exception):
    def __init__(self, message: str):
        super().__init__(f"ERROR: {message}")


class FileException(Error):
    def __init__(self, message: str, path: str = DefaultPath):
        if (path != DefaultPath):
            message += f" at {path}"

        super().__init__(message)


class DuplicateFileException(FileException):
    def __init__(self, fileType: str = DefaultFileType, path: str = DefaultPath):
        message = f"Ensure only one {fileType} exists"
        super().__init__(message, path = path)


class MissingFileException(FileException):
    def __init__(self, fileType: str = DefaultFileType, path: str = DefaultPath):
        message = f"Unable to find {fileType}. Ensure it is in the folder"
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
                raise DuplicateFileException(fileType = fileType, path = path)
            
            if (fileTypeFiles):
                result.append(fileTypeFiles[0])
            else:
                result.append(None)
            i += 1

        if (onlyOneFilter):
            return result[0]
        
        return result


class Logger():
    def __init__(self, prefix: str = ""):
        self.prefix = prefix

    def getStr(self, message: str):
        return f"# {self.prefix} --> {message}"

    def log(self, message: str):
        print(self.getStr(message))

    def split(self) -> str:
        self.log("\n")

    def space(self) -> str:
        self.log("")

    def error(self, message: str):
        self.space()
        self.log("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

        messageList = message.split("\n")
        for messagePart in messageList:
            self.log(messagePart)

        self.log("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    def handleException(self, exception: BaseException):
        message = f"\n{type(exception).__name__}: {exception}\n\n{traceback.format_exc()}"
        self.error(message)

    def waitExit(self):
        input("\n== Press ENTER to exit ==")


# Needed data model to inject into the .ini file
class RemapBlendModel():
    def __init__(self, fixedBlendName: str, draw: str, path: str):
        self.fixedBlendName = fixedBlendName
        self.draw = draw
        self.path = path
        self.blendPath = os.path.join(self.path, f"{self.fixedBlendName}.buf")


class IniFile():
    Credit = f'\n; Raiden boss fixed by NK#1321 if you used it for fix your raiden pls give credit for "Nhok0169"\n; Thank nguen#2011 SilentNightSound#7430 HazrateGolabi#1364 and Albert Gold#2696 for support'

    _fixHeader = "; --------------- Raiden Boss Fix -----------------"
    _fixFooter = "; -------------------------------------------------"

    _textureOverrideBlendPattern = re.compile(r"\[\s*TextureOverride(\w+)Blend\s*\]")
    _resourceBlendPattern = re.compile(r"\[\s*Resource((?!RaidenShogunRemap).)*Blend\.[0-9]+\s*\]")

    _fixedTextureOverrideBlendPatternStr = r"\[\s*TextureOverrideRaidenShogunRemapBlend\s*\]"
    _fixedCommandListBlendPatternStr = r"\[\s*CommandListRaidenShogunRemapBlend\s*\]"
    _fixedMergedResourceBlendPatternStr = r"\[\s*ResourceRaidenShogunRemapBlend\.[0-9]+\s*\]"
    _fixedBaseResourceBlendPatternStr = r"\[\s*ResourceRaidenShogunRemapBlend\s*\]"

    _fixedTextureOverrideBlendPattern = re.compile(_fixedTextureOverrideBlendPatternStr)

    _mergedSectionsRemovalPattern = re.compile(f"({_fixedTextureOverrideBlendPatternStr})|({_fixedCommandListBlendPatternStr})|({_fixedMergedResourceBlendPatternStr})")
    _baseSectionsRemovalPattern = re.compile(f"({_fixedTextureOverrideBlendPatternStr})|({_fixedBaseResourceBlendPatternStr})")
    _fixRemovalPattern = re.compile(f"{_fixHeader}(.|\n)*{_fixFooter}")

    def __init__(self, file: str):
        self.file = file
        self._parser = configparser.ConfigParser()

        self._fileLines = []
        self._fileTxt = ""
        self._fileLinesRead = False
        self._isRaidenFixed = False
        self._merged = self.isMerged()

    @property
    def isRaidenFixed(self):
        return self._isRaidenFixed

    def isMerged(self) -> bool:
        return self.file.endswith(MergedFile)
    
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

    def _parseSection(self, sectionName: str, srcTxt: str):
        self._parser.read_string(srcTxt)
        return dict(self._parser[sectionName])

    # retrieves the key-value pairs of a section in the .ini file. Manually parsed the file since ConfigParser
    #   errors out on conditional statements in .ini file for mods. Could later inherit from the parser (RawConfigParser) 
    #   to custom deal with conditionals
    @_readLines
    def getSectionOptions(self, section: str, postProcessor: Optional[Callable[[int, List[str], str, str], Any]] = None) -> Dict[str, Dict[str, Any]]:
        sectionFilter = None
        if (isinstance(section, str)):
            sectionFilter = lambda line: line == section
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

    def getTextureOverideBlendDicts(self) -> Dict[str, Dict[str, Any]]:
        return self.getSectionOptions(self._textureOverrideBlendPattern)
    
    def getResourceBlendDicts(self) -> Dict[str, Dict[str, Any]]:
        return self.getSectionOptions(self._resourceBlendPattern)

    # get the needed draw value
    def getBlendDrawValue(self, textureOverideKvps: Dict[str, Any]) -> Optional[str]:
        if textureOverideKvps["draw"]:
            draw: str = textureOverideKvps["draw"]
        return draw
    
    def getMergedResourceIndex(self, mergedResourceName: str) -> str:
        return mergedResourceName.split(".")[-1]

    # get the sorted order of the mod folders used in the merged.ini
    def getResourceBlendFolderPaths(self, resourceDicts: Dict[str, Dict[str, Any]]) -> List[str]:
        fileNameKey = "filename"
        modFolders = []

        # case where the resources are not put in the proper order
        resourceTuples = [(k, v) for k, v in resourceDicts.items()]
        resourceTuples.sort(key = lambda tuple: int(self.getMergedResourceIndex(tuple[0])))

        for tuple in resourceTuples:
            resourceDict = tuple[1]

            # normalize by ntpath for linux users
            if (resourceDict[fileNameKey]):
                resourcePath = ntpath.normpath(resourceDict[fileNameKey])
                folderPath = ntpath.dirname(resourcePath)
                modFolders.append(folderPath)

        return modFolders

    # Disabling the OLD ini
    def disIni(self):
        baseName = os.path.basename(self.file)

        if (baseName.endswith(IniExt)):
            baseName = baseName[:-IniExtLen] + TxtExt

        backupFile = os.path.join(os.path.dirname(self.file), BackupFilePrefix) + baseName

        try:
            os.rename(self.file, backupFile)
        except FileExistsError:
            os.remove(backupFile)
            os.rename(self.file, backupFile)

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
        return f"Resource{name}"
    
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
            resourceName = f"{cls.getResourceName(model.fixedBlendName)}.{i}"

            if (i):
                result += "\n\n"

            result += cls.getResource(resourceName, model.blendPath)

        return result
    
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

            addFix += f"if $swapvar == {i}\n\tvb1 = {cls.getResourceName(model.fixedBlendName)}.{i}\n\thandling = skip\n\tdraw = {model.draw}"

        addFix += "\nendif"
        return addFix

    # get the needed lines to add to the each individual *.ini file
    @classmethod
    @_addFixBoilerPlate
    def getBaseFixStr(cls, fixedBlendName: str, draw: str) -> str:
        resourceName = cls.getResourceName(fixedBlendName)

        addFix = f"\n\n{cls.getTextureOverride(fixedBlendName)}\nvb1 = {cls.getResourceName(fixedBlendName)}\nhandling = skip\ndraw = {draw} "
        addFix += f'\n\n{cls.getResource(resourceName, f"{fixedBlendName}.buf")}'

        return addFix

    # get the needed lines to add to the merged.ini file
    @classmethod
    @_addFixBoilerPlate
    def getMergedFixStr(cls, globalBlendName: str, remapBlendModels: List[RemapBlendModel]) -> str:
        commandName = cls.getCommandName(globalBlendName)
        addFix = f"\n\n{cls.getTextureOverride(globalBlendName)}"
        addFix += f"\nrun = {commandName}"
        addFix += f"\n\n{cls.getRemapCommand(commandName, remapBlendModels)}"
        addFix += f"\n\n{cls.getResources(remapBlendModels)}"

        return addFix

    @_readLines
    def injectAddition(self, addition: str, logger: Optional[Logger] = None, beforeOriginal: bool = True, keepBackup: bool = True, fixOnly: bool = False):
        original = "".join(self._fileLines)

        if (keepBackup and fixOnly):
            if (logger is not None):
                logger.log("Cleaning up and disabling the OLD STINKY ini")

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

    def removeBaseFix(self):
        self._removeScriptFix()
        self.getFileLines()
        self.removeSectionOptions(self._baseSectionsRemovalPattern)
        self.write()
        self.clearRead()

    def removeMergedFix(self):
        self._removeScriptFix()
        self.getFileLines()
        self.removeSectionOptions(self._mergedSectionsRemovalPattern)
        self.write()
        self.clearRead()

    @_readLines
    def removeFix(self, logger: Optional[Logger] = None, keepBackups: bool = True, fixOnly: bool = False):
        hasLogger = bool(logger is not None)
        if (keepBackups and not fixOnly):
            if (hasLogger):
                logger.log(f"Creating Backup for {os.path.basename(self.file)}")

            self.disIni()

        if (hasLogger):
            logger.log(f"Removing any previous changes from this script in {os.path.basename(self.file)}")

        if (self._merged):
            self.removeMergedFix()
            return

        self.removeBaseFix()

    def fixBase(self, remapBlendModel: RemapBlendModel, logger: Optional[Logger] = None, keepBackup: bool = True, fixOnly: bool = False):
        addFix = self.getBaseFixStr(remapBlendModel.fixedBlendName, remapBlendModel.draw)
        self.injectAddition(addFix, logger = logger, keepBackup = keepBackup, fixOnly = fixOnly)

    def fixMerged(self, remapBlendModels: List[RemapBlendModel], logger: Optional[Logger] = None, keepBackup: bool = True, fixOnly: bool = False):
        addFix = self.getMergedFixStr(remapBlendModels[0].fixedBlendName, remapBlendModels)
        self.injectAddition(f"\n\n{addFix}", logger = logger, beforeOriginal = False, keepBackup = keepBackup, fixOnly = fixOnly)


class Mod():
    def __init__(self, path: str = DefaultPath, files: Optional[List[str]] = None, isTopMod: bool = False):
        self.path = path
        self.isTopMod = isTopMod
        self._files = files
        self._setupFiles()

        if (self.isTopMod):
            self.ini = self.getBaseModFiles()
            self.backupIni, self.remapBlend, self.blend = self.getOptionalFiles()
        else:
            self.ini, self.blend = self.getBaseModFiles()
            self.backupIni, self.remapBlend = self.getOptionalFiles()

        self.ini = IniFile(self.ini)

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
    
    def getBaseModFiles(self) -> List[str]:
        filters = {IniFileType: self.isIni}
        if (not self.isTopMod):
            filters[BlendFileType] =  self.isBlend

        return FileService.getSingleFiles(path = self.path, filters = filters, files = self._files)
    
    def getOptionalFiles(self) -> List[Optional[str]]:
        filters = {"Backup Ini": self.isBackupIni, "Remap Blend": self.isRemapBlend}
        if (self.isTopMod):
            filters[BlendFileType] = self.isBlend

        return FileService.getSingleFiles(path = self.path, filters = filters, files = self._files, optional = True)
    
    def removeBackupIni(self, logger: Optional[Logger] = None):
        if (self.backupIni is not None):
            if (logger is not None):
                logger.log(f"Removing the backup ini, {os.path.basename(self.backupIni)}")

            os.remove(self.backupIni)

    def removeFix(self, logger: Optional[Logger] = None, keepBackups: bool = True, fixOnly: bool = False):
        hasLogger = bool(logger is not None)

        if (self.remapBlend is not None):
            if (hasLogger):
                logger.log(f"Removing previous {RemapBlendFile}")
            os.remove(self.remapBlend)

        self.ini.removeFix(logger = logger, keepBackups = keepBackups, fixOnly = fixOnly)


class RaidenBossFixService():
    def __init__(self, keepBackups: bool = True, fixOnly: bool = False, undoOnly: bool = False):
        self._loggerBasePrefix = ""
        self._logger = Logger()
        self._keepBackups = keepBackups
        self._fixOnly = fixOnly
        self._undoOnly = undoOnly


    def getFixedBlendFile(self, blendFile: str) -> str:
        return f"{blendFile.split('Blend.buf')[0]}RemapBlend.buf"

    # correcting the blend file
    def _blendCorrection(self, blendFile: str) -> str:
        self._logger.log("Correcting the blend file")

        with open(blendFile, "rb") as f:
            blendData = f.read()

        if len(blendData)%32 != 0:
            self._logger.log()
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
        self._logger.log('Blend file correction done')
        return fixedBlendFile

    # fix each individual mod containing the assets
    def fixBaseMod(self, mod: Mod) -> Optional[RemapBlendModel]:
        # remove any backups
        if (not self._keepBackups):
            mod.removeBackupIni(logger = self._logger)

        # undo any previous fixes
        if (not self._fixOnly):
            mod.removeFix(logger = self._logger, keepBackups = self._keepBackups)

        if (self._undoOnly):
            return

        textureOverideBlendDicts = mod.ini.getTextureOverideBlendDicts()
        draw = mod.ini.getBlendDrawValue(DictTools.getFirstValue(textureOverideBlendDicts))

        fixedBlendName = self.getFixedBlendFile(mod.blend)
        fixedBlendName = os.path.basename(fixedBlendName).split('.')[0]

        remapBlendModel = RemapBlendModel(fixedBlendName, draw, mod.path)

        self._blendCorrection(mod.blend)
        if (mod.ini.isRaidenFixed):
            self._logger.log("ini file already fixed")
            return remapBlendModel

        # writing the fixed file
        self._logger.log("Making the fixed ini file")
        mod.ini.fixBase(remapBlendModel, logger = self._logger, keepBackup = self._keepBackups, fixOnly = self._fixOnly)
        return remapBlendModel


    def _fix(self):
        if (self._fixOnly and self._undoOnly):
            raise ConflictingOptions([FixOnlyOpt, RevertOpt])

        modFolder = os.path.basename(os.getcwd())
        self._loggerBasePrefix = modFolder
        self._logger.prefix = self._loggerBasePrefix

        files, dirs = FileService.getFilesAndDirs()
        topMod = Mod(files = files, isTopMod = True)
        topIni = topMod.ini

        if (topIni.isMerged()):
            self._logger.log("Fixing Merged Mod")
            self._logger.log(f"Reading {MergedFile} file for individual mods to modify")

            # read the merged.ini for mod folders
            resourceBlendDicts = topIni.getResourceBlendDicts()
            modFolders = topIni.getResourceBlendFolderPaths(resourceBlendDicts)

            # remove any backups
            if (not self._keepBackups):
                topMod.removeBackupIni(logger = self._logger)

            # undo any previous fixes
            if (not self._fixOnly):
                topMod.removeFix(logger = self._logger, keepBackups = self._keepBackups)

            remapBlendModelsDict = {}
            remapBlendModels = []
            for dir in modFolders:
                dirName = dir.replace(ntpath.sep, os.sep)

                # case where a mod folder is called twice in merged.ini
                try:
                    remapBlendModelsDict[dirName]
                except:
                    pass
                else:
                    remapBlendModels.append(remapBlendModelsDict[dirName])
                    continue

                mod = None
                try:
                    mod = Mod(path = dirName)
                except FileException as e:
                    continue

                self._logger.split()
                self._logger.prefix = f"{self._loggerBasePrefix} --> {dirName.replace(os.sep, ' --> ')}"

                remapBlendModel = self.fixBaseMod(mod)
                if (self._undoOnly):
                    continue

                remapBlendModels.append(remapBlendModel)
                remapBlendModelsDict[dirName] = remapBlendModel

            self._logger.split()
            self._logger.prefix = self._loggerBasePrefix

            if (self._undoOnly):
                self._logger.log("Finished reverting previous changes")
                return

            if (not remapBlendModels):
                self._logger.log("No mods found for the merged mod or all mods have already been converted")
                return

            if (topIni.isRaidenFixed):
                self._logger.log(f"{MergedFile} file already fixed")
                return

            self._logger.log(f"Making the {MergedFile} file")
            topIni.fixMerged(remapBlendModels, logger = self._logger, keepBackup = self._keepBackups, fixOnly = self._fixOnly)
        else:
            self._logger.log("Fixing Single Mod")
            self.fixBaseMod(topMod)

        self._logger.log("ENJOY")


    def fix(self):
        try:
            self._fix()
        except BaseException as e:
            self._logger.handleException(e)

        self._logger.waitExit()


# Main Driver Code
if __name__ == "__main__":
    args = argParser.parse_args()
    raidenBossFixService = RaidenBossFixService(keepBackups = not args.deleteBackup, fixOnly = args.fixOnly, undoOnly = args.revert)
    raidenBossFixService.fix()