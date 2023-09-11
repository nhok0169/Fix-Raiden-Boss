# Author: NK#1321 raiden boss fix, if you used it to fix your raiden pls give credit for "Nhok0169"
# Special Thanks:
#   nguen#2011 (for support)
#   SilentNightSound#7430 (for internal knowdege so wrote the blendCorrection code)
#   HazrateGolabi#1364 (for being awesome, and improving the code)


import os
import configparser
import re
import struct
import traceback
from typing import List, Callable, Optional, Union, Dict, Any



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

DefaultFileType = "file"
DefaultPath = "."
IniExt = ".ini"
MergedFile = f"merged{IniExt}"

IniFileType = "*.ini file"
BlendFileType = "Blend.buf"


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
    def getSingleFiles(cls, path: str = DefaultPath, filters: Dict[str, Callable[[str], bool]] = {}, files: Optional[List[str]] = None) -> Union[str, List[str]]:
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

            if (not filesLen):
                raise MissingFileException(fileType = fileType, path = path)
            elif (filesLen > 1):
                raise DuplicateFileException(fileType = fileType, path = path)
            
            result.append(fileTypeFiles[0])
            i += 1

        if (onlyOneFilter):
            return result[0]
        
        return result
    

class ModFileService():
    @classmethod
    def isMerged(cls, file: str) -> bool:
        return file.endswith(MergedFile)

    @classmethod
    def isIni(cls, file: str) -> bool:
        return file.endswith(IniExt)
    
    @classmethod
    def isBlend(cls, file: str) -> bool:
        return file.endswith(BlendFileType)
    
    @classmethod
    def getBaseModFiles(cls, files: Optional[List[str]] = None, path: str = DefaultPath) -> List[str]:
        return FileService.getSingleFiles(path = path, filters = {IniFileType: cls.isIni, BlendFileType: cls.isBlend}, files = files)
    
    @classmethod
    def getIni(cls, files: Optional[List[str]] = None, path: str = DefaultPath) -> str:
        return FileService.getSingleFiles(path = path, filters = {IniFileType: cls.isIni}, files = files)

    @classmethod
    def getBlend(cls, files: Optional[List[str]] = None, path: str = DefaultPath) -> str:
        return FileService.getSingleFiles(path = path, filters = {BlendFileType: cls.isBlend}, files = files)


class Logger():
    def __init__(self, prefix: str = ""):
        self.prefix = prefix

    def getStr(self, message: str):
        return f"# {self.prefix} --> {message}"

    def log(self, message: str):
        print(self.getStr(message))

    def split(self) -> str:
        self.log("\n")

    def error(self, message: str):
        self.log("")
        self.log("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

        messageList = message.split("\n")
        for messagePart in messageList:
            self.log(messagePart)

        self.log("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    def handleException(self, exception: BaseException):
        message = f"\n{type(exception).__name__}: {exception}\n\n{traceback.format_exc()}"
        self.error(message)


# Needed data model to inject into the .ini file
class RemapBlendModel():
    def __init__(self, fixedBlendName: str, draw: str, path: str):
        self.fixedBlendName = fixedBlendName
        self.draw = draw
        self.path = path
        self.blendPath = os.path.join(self.path, f"{self.fixedBlendName}.buf")


class IniFileService():
    Credit = f'\n; raiden boss fixed by NK#1321 if you used it for fix your raiden pls give credit for "Nhok0169"\n; thank nguen#2011 SilentNightSound#7430 and HazrateGolabi#1364 for support'

    def __init__(self, parser: configparser.ConfigParser):
        self._parser = parser
        self._textureOverrideBlendPattern = re.compile(r"\[\s*TextureOverride(\w+)Blend\s*\]")
        self._resourceBlendPattern = re.compile(r"\[\s*Resource(\w+)Blend\.[0-9]+\s*\]")
    
    @classmethod
    def getFileLines(cls, iniFile: str) -> List[str]:
        content = ""
        with open(iniFile, "r") as f:
            content = f.readlines()
        return content

    # retrieves the key-value pairs of a section in the .ini file. Manually parsed the file since ConfigParser
    #   errors out on conditional statements in .ini file for mods. Could later inherit from the parser(RawConfigParser) 
    #   to custom deal with conditionals
    def getSectionOptions(self, iniFileLines: List[str], section: Union[str, re.Pattern]) -> List[Dict[str, Any]]:
        sectionFilter = None
        if (isinstance(section, str)):
            sectionFilter = lambda line: line == section
        else:
            sectionFilter = lambda line: section.match(line)

        result = []
        currentSectionName = None
        currentSectionToParse = None

        for line in iniFileLines:
            if (sectionFilter(line)):
                currentSectionToParse = f"{line}"
                currentSectionName = line.strip().replace("]", "")
                currentSectionName = currentSectionName.replace("[", "")
                continue

            if (currentSectionToParse is None):
                continue

            if (line.strip() == ""):
                self._parser.read_string(currentSectionToParse)
                result.append(dict(self._parser[currentSectionName]))

                currentSectionToParse = None
                currentSectionName = None
            else:
                currentSectionToParse += f"{line}"

        return result

    def getTextureOverideBlendDicts(self, iniFileLines: List[str]):
        return self.getSectionOptions(iniFileLines, self._textureOverrideBlendPattern)
    
    def getResourceBlendDicts(self, iniFileLines: List[str]):
        return self.getSectionOptions(iniFileLines, self._resourceBlendPattern)

    # get the needed draw value
    def getBlendDrawValue(self, textureOverideKvps: Dict[str, Any]) -> Optional[str]:
        if textureOverideKvps["draw"]:
            draw: str = textureOverideKvps["draw"]
        return draw

    # get the sorted order of the mod folders used in the merged.ini
    def getResourceBlendFolderPaths(self, resourceDicts: List[Dict[str, Any]]) -> List[str]:
        fileNameKey = "filename"
        modFolders = []

        for resourceDict in resourceDicts:
            if (resourceDict[fileNameKey]):
                folder = os.path.dirname(resourceDict[fileNameKey])
                modFolders.append(folder)

        return modFolders

    # Disabling the OLD ini
    @classmethod
    def disIni(cls, file: str):
        try:
            os.rename(file, os.path.join(os.path.dirname(file), "DISABLED") + os.path.basename(file))
        except FileExistsError:
            pass

    @classmethod
    def getFixHeader(cls) -> str:
        return "; --------------- Raiden Boss Fix -----------------"
    
    @classmethod
    def getFixFooter(cls) -> str:
        return "\n\n; -------------------------------------------------"

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

    @classmethod
    def injectAddition(cls, iniFile: str, addition: str, logger: Optional[Logger] = None, beforeOriginal: bool = True):
        original = ''
        with open(iniFile, "r") as f:
            original = f.read()

        if (logger is not None):
            logger.log("Cleaning up and disabling the OLD STINKY ini")  
        cls.disIni(iniFile)

        # writing the fixed file
        with open(iniFile, "w") as f:
            if (beforeOriginal):
                f.write(addition)

            f.write(f"\n\n{original}")

            if (not beforeOriginal):
                f.write(addition)

    @classmethod
    def fixBase(cls, iniFile: str, remapBlendModel: RemapBlendModel, logger: Optional[Logger] = None):
        addFix = cls.getBaseFixStr(remapBlendModel.fixedBlendName, remapBlendModel.draw)
        cls.injectAddition(iniFile, addFix, logger = logger)

    @classmethod
    def fixMerged(cls, iniFile: str, remapBlendModels: List[RemapBlendModel], logger: Optional[Logger] = None):
        addFix = cls.getMergedFixStr(remapBlendModels[0].fixedBlendName, remapBlendModels)
        cls.injectAddition(iniFile, f"\n\n{addFix}", logger = logger, beforeOriginal = False)


class RaidenBossFixService():
    def __init__(self):
        self._parser = configparser.ConfigParser()
        self._iniFileService = IniFileService(self._parser)
        self._loggerBasePrefix = ""
        self._logger = Logger()

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
        FixedBlendName = f"{blendFile.split('Blend.buf')[0]}RemapBlend.buf"
        with open(FixedBlendName, "wb") as f:
            f.write(result)
        self._logger.log('Blend file correction done')
        return FixedBlendName

    # fix each individual mod containing the assets
    def fixBaseMod(self, path: str = DefaultPath, iniFile: Optional[str] = None, blendFile: Optional[str] = None, files: Optional[List[str]] = None) -> RemapBlendModel:
        if (iniFile is None and blendFile is None):
            iniFile, blendFile = ModFileService.getBaseModFiles(path = path, files = files)
        elif (iniFile is None):
            iniFile = ModFileService.getIni(path = path, files = files)
        elif (blendFile is None):
            blendFile = ModFileService.getBlend(path = path, files = files)

        iniLines = self._iniFileService.getFileLines(iniFile)
        textureOverideBlendDicts = self._iniFileService.getTextureOverideBlendDicts(iniLines)
        draw = self._iniFileService.getBlendDrawValue(textureOverideBlendDicts[0])

        fixedBlendName = self._blendCorrection(blendFile)
        fixedBlendName = os.path.basename(fixedBlendName).split('.')[0]
        
        remapBlendModel = RemapBlendModel(fixedBlendName, draw, path)

        # writing the fixed file
        self._logger.log("Making the fixed ini file")
        self._iniFileService.fixBase(iniFile, remapBlendModel, logger = self._logger)

        return remapBlendModel


    def _fix(self):
        modFolder = os.path.basename(os.getcwd())
        self._loggerBasePrefix = modFolder
        self._logger.prefix = self._loggerBasePrefix

        files, dirs = FileService.getFilesAndDirs()
        topIniFile = ModFileService.getIni(files = files)

        if (ModFileService.isMerged(topIniFile)):
            self._logger.log(f"Reading {MergedFile} file for individual mods to modify")

            # read the merged.ini for mod folders
            iniLines = self._iniFileService.getFileLines(topIniFile)
            resourceBlendDicts = self._iniFileService.getResourceBlendDicts(iniLines)

            modFolders = self._iniFileService.getResourceBlendFolderPaths(resourceBlendDicts)
            remapBlendModelsDict = {}
            remapBlendModels = []
            for dir in modFolders:
                blendFile =""
                iniFile = ""
                dirBaseName = os.path.basename(dir)

                # case where a mod folder is called twice in merged.ini
                try:
                    remapBlendModelsDict[dir]
                except:
                    pass
                else:
                    remapBlendModels.append(remapBlendModelsDict[dir])
                    continue

                try:
                    iniFile, blendFile = ModFileService.getBaseModFiles(path = dir)
                except FileException as e:
                    continue

                self._logger.split()
                self._logger.prefix = f"{self._loggerBasePrefix} --> {dirBaseName}"

                remapBlendModel = self.fixBaseMod(path = dir, iniFile = iniFile, blendFile = blendFile)
                remapBlendModels.append(remapBlendModel)
                remapBlendModelsDict[dir] = remapBlendModel

            if (not remapBlendModels):
                self._logger.log("No mods found for the merged mod or all mods have already been converted")
                return

            self._logger.split()
            self._logger.prefix = self._loggerBasePrefix
            self._logger.log(f"Making the {MergedFile} file")
            self._iniFileService.fixMerged(topIniFile, remapBlendModels, logger = self._logger)
        else:
            self.fixBaseMod(iniFile = topIniFile, files = files)

        self._logger.log("ENJOY")


    def fix(self):
        try:
            self._fix()
        except BaseException as e:
            self._logger.handleException(e)


# Main Driver Code
raidenBossFixService = RaidenBossFixService()
raidenBossFixService.fix()