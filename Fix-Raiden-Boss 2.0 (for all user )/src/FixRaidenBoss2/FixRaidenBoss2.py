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
Pattern = TypeVar('Pattern')
TextIoWrapper = TypeVar('TextIoWrapper')


class Error(Exception):
    """
    The base exception used by this module

    Parameters
    ----------
    message: :class:`str`
        the error message to print out
    """

    def __init__(self, message: str):
        super().__init__(f"ERROR: {message}")

    def warn(self):
        """
        Retrieves the warning message for the exception
        """
        return str(self).replace("ERROR", "WARNING")


class FileException(Error):
    """
    This Class inherits from :class:`Error`

    Exceptions relating to files

    Parameters
    ----------
    message: :class:`str`
        The error message to print out

    path: Optional[:class:`str`]
        The path where the error for the file occured. If this value is ``None``, then the path
        will be the current directory where this module is loaded :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``None``
    """

    def __init__(self, message: str, path: Optional[str] = None):
        path = FileService.getPath(path)

        if (path != DefaultPath):
            message += f" at {path}"

        super().__init__(message)


class DuplicateFileException(FileException):
    """
    This Class inherits from :class:`FileException`

    Exception when there are multiple files of the same type in a folder

    Parameters
    ----------
    files: List[:class:`str`]
        The files that triggered the exception

    fileType: :class:`str`
        The name for the type of files :raw-html:`<br />` :raw-html:`<br />`

        **Default**: "file"

    path: Optional[:class:`str`]
        The path to the folder where the files are located If this value is ``None``, then the path
        will be the current directory where this module is loaded :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``None``

    Attributes
    ----------
    files: List[:class:`str`]
        The files that triggered the exception

    fileType: :class:`str`
        The name for the type of files

        **Default**: ``None``
    """

    def __init__(self, files: List[str], fileType: str = DefaultFileType, path: Optional[str] = None):
        path = FileService.getPath(path)
        self.files = files
        self.fileType = fileType
        message = f"Ensure only one {fileType} exists"
        super().__init__(message, path = path)


class MissingFileException(FileException):
    """
    This Class inherits from :class:`FileException`

    Exception when a certain type of file is missing from a folder

    Parameters
    ----------
    fileType: :class:`str`
        The type of file searching in the folder :raw-html:`<br />` :raw-html:`<br />`

        **Default**: "file"

    path: :class:`str`
        The path to the folder that is being searched. If this value is ``None``, then the path
        will be the current directory where this module is loaded :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``None``

    Attributes
    ----------
    fileType: :class:`str`
        The type of file searching in the folder
    """
    def __init__(self, fileType: str = DefaultFileType, path: Optional[str] = None):
        path = FileService.getPath(path)
        message = f"Unable to find {fileType}. Ensure it is in the folder"
        self.fileType = fileType
        super().__init__(message, path = path)


class BlendFileNotRecognized(FileException):
    """
    This Class inherits from :class:`FileException`

    Exception when a Blend.buf file cannot be read

    Parameters
    ----------
    blendFile: :class:`str`
        The file path to the Blend.buf file
    """
    def __init__(self, blendFile: str):
        super().__init__(f"Blend file format not recognized for {os.path.basename(blendFile)}", path = os.path.dirname(blendFile))


class ConflictingOptions(Error):
    """
    This Class inherits from :class:`Error`

    Exception when the script or :class:`RaidenBossFixService` is ran with options that cannot be used together

    Parameters
    ----------
    options: List[:class:`str`]
        The options that cannot be used together
    """
    def __init__(self, options: List[str]):
        optionsStr = ", ".join(options)
        super().__init__(f"The following options cannot be used toghether: {optionsStr}")


class DictTools():
    """
    Tools for handling with Dictionaries
    """

    @classmethod
    def getFirstKey(cls, dict: Dict[Any, Any]) -> Any:
        """
        Retrieves the first key in a dictionary

        Parameters
        ----------
        dict: Dict[Any, Any]
            The dictionary we are working with

        Returns
        -------
        Any
            The first key of the dictionary
        """

        return next(iter(dict))

    @classmethod
    def getFirstValue(cls, dict: Dict[Any, Any]) -> Any:
        """
        Retrieves the first value in a dictionary

        Parameters
        ----------
        dict: Dict[Any, Any]
            The dictionary we are working with

        Returns
        -------
        Any
            The first value of the dictionary
        """

        return dict[cls.getFirstKey(dict)]
    
    # combine(dst, src, combine_duplicate): Combines dictionaries to 'dst'
    @classmethod
    def combine(cls, dst: Dict[Hashable, Any], src: Dict[Hashable, Any], combineDuplicate: Optional[Callable[[Any, Any], Any]] = None):
        """
        Combines 2 dictionaries

        Parameters
        ----------
        dst: Dict[Hashable, Any]
            The destination of where we want the combined dictionaries to be stored

        src: Dict[Hashable, Any]
            The that we want to combine values with

        combineDuplicate: Optional[Callable[[Any, Any], Any]]
            Function for handling cases where there contains the same key in both dictionaries

            If this value is set to ``None``, then will use the key from 'dst' :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ``None``
        """

        if (combineDuplicate is None):
            dst.update(src)
            return dst
        
        new_dict = {**dst, **src}
        for key, value in new_dict.items():
            if key in dst and key in src:
                new_dict[key] = combineDuplicate(value, src[key])
        return new_dict
    

class ListTools():
    """
    Tools for handling with lists
    """

    @classmethod
    def to_dict(cls, lst: List[T], get_id: Callable[[T], Hashable]) -> Dict[Hashable, T]:
        """
        Turns a list into a dictionary

        Parameters
        ----------
        lst: List[T]
            The list that we want to turn into a dictionary

        get_id: Callable[[T], Hashable]
            The function for generating ids for the list

        Returns
        -------
        Dict[Hashable, T]
            The transformed dictionary from the list
        """

        return {get_id(e): e for e in lst}

    @classmethod
    def getDistinct(cls, lst: List[T]) -> List[T]:
        """
        Retrieves a list with distinct values

        Parameters
        ----------
        lst: List[T]
            The list that we are working with

        Returns
        -------
        List[T]
            A list where all values are distinct
        """

        return list(dict.fromkeys(lst))


class FileService():
    """
    Tools for handling with files and folders :raw-html:`<br />` :raw-html:`<br />`
    """

    @classmethod
    def getFilesAndDirs(cls, path: Optional[str] = None, recursive: bool = False) -> List[List[str]]:
        """
        Retrieves the files and folders contained in a certain folder

        Parameters
        ----------
        path: Optional[:class:`str`]
            The path to the target folder we are working with. If this argument is ``None``, then will use the current directory of where this module is loaded
            :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ``None``

        recursive: :class:`bool`
            Whether to recursively check all the folders from our target folder :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ``False``

        Returns
        -------
        [List[:class:`str`], List[:class:`str`]]
            The files and directories within the folder. The order for the result is:

            #. files
            #. folders
        """
        path = cls.getPath(path)
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
        """
        Checks whether a file path is a file

        Parameters
        ----------
        path: :class:`str`
            The file path to the folder where the file is contained

        file: :class:`str`
            The name of the file

        Returns
        -------
        :class:`bool`
            Whether the combined file path is a file
        """

        fullPath = os.path.join(path, file)
        return os.path.isfile(fullPath)

    # filters and partitions the files based on the different filters specified
    @classmethod
    def getFiles(cls, path: Optional[str] = None, filters: List[Callable[[str], bool]] = [], files: Optional[List[str]] = None) -> Union[List[str], List[List[str]]]:
        """
        Retrieves many different types of files within a folder

        Parameters
        ----------
        path: Optional[:class:`str`]
            The path to the target folder we are working with. If this value is set to ``None``, then will use the current directory of where this module is loaded
            :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ``None``

        filters: List[Callable[[:class:`str`], :class:`bool`]]
            Different filter functions for each type of file we are trying to get :raw-html:`<br />` :raw-html:`<br />`

            **Default**: []

        files: Optional[List[:class:`str`]]
            The files contained in the target folder

            If this value is set to ``None``, then the function will search for the files :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ``None``

        Returns
        -------
        Union[List[:class:`str`], List[List[:class:`str`]]]
            The files partitioned into the different types specified by the filters

            If 'filters' only has 1 element, then the function returns List[:class:`str`]
            Otherwise, will return List[List[:class:`str`]]
        """

        path = cls.getPath(path)
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
    def getSingleFiles(cls, path: Optional[str] = None, filters: Dict[str, Callable[[str], bool]] = {}, files: Optional[List[str]] = None, optional: bool = False) -> Union[Optional[str], List[str], List[Optional[str]]]:
        """
        Retrieves exactly 1 of each type of file in a folder

        Parameters
        ----------
        path: Optional[:class:`str`]
            The path to the target folder we are searching. :raw-html:`<br />` :raw-html:`<br />`
            
            If this value is set to ``None``, then will use the current directory of where this module is loaded :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ``None``

        filters: Dict[str, Callable[[:class:`str`], :class:`bool`]]
            Different filter functions for each type of file we are trying to get.

            The keys are the names for the file type :raw-html:`<br />` :raw-html:`<br />`

            **Default**: {}

        files: Optional[List[:class:`str`]]
            The files contained in the target folder

            If this value is set to ``None``, then the function will search for the files :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ``None``

        optional: :class:`bool`
            Whether we want to send an exception if there is not exactly 1 file for a certain type of file :raw-html:`<br />` :raw-html:`<br />`

            #. If this value is ``False`` and there are no files for a certain type of file, then will raise a :class:`MissingFileException`
            #. If this value is ``False`` and there are more than 1 file for a certain type of file, then will raise a :class:`DuplicateFileException`
            #. If this value is ``True`` and there are no files for a certain type of file, then the file for that type of file will be ``None``
            #. If this value is ``True`` and there are more than 1 file for a certain type of file, then will retrieve the first file for that type of file :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ``False``

        Raises
        ------
        :class:`MissingFileException`
            if ``optional`` is set to ``False`` and there are not files for a certain type of file

        :class:`DuplicateFileException`
            if ``optional`` is set to ``False`` and there are more than 1 file for a certain type of file

        Returns
        -------
        Union[Optional[:class:`str`], List[:class:`str`], List[Optional[:class:`str`]]]
            The files partitioned for each type of file

            * If ``filters`` only contains 1 element and ``optional`` is ``False``, then will return :class:`str`
            * If ``filters`` contains more than 1 element and ``optional`` is ``False`, then will return List[:class:`str`]
            * If ``filters`` only contains 1 element and ``optional`` is ``True``, then will return Optional[:class:`str`]
            * Otherwise, returns List[Optional[:class:`str`]]
        """
        path = cls.getPath(path)
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
        """
        Renames a file

        .. warning::
            If the new name for the file already exists, then the function deletes
            the file with the new name and renames the target file with the new name

        Parameters
        ----------
        oldFile: :class:`str`
            file path to the target file we are working with

        newFile: :class:`str`
            new file path for the target file 
        """

        try:
            os.rename(oldFile, newFile)
        except FileExistsError:
            os.remove(newFile)
            os.rename(oldFile, newFile)

    @classmethod
    def changeExt(cls, file: str, newExt: str) -> str:
        """
        Changes the extension for a file

        Parameters
        ----------
        file: :class:`str`
            The file path to the file we are working with

        newExt: :class:`str`
            The name of the new extension for the file (without the dot at front)

        Returns
        -------
        :class:`str`
            the new file path with the extension changed
        """

        dotPos = file.rfind(".")

        if (not newExt.startswith(".")):
            newExt = f".{newExt}"

        if (dotPos != -1):
            file = file[:dotPos] + newExt

        return file

    @classmethod
    def disableFile(cls, file: str, filePrefix: str = BackupFilePrefix):
        """
        Marks a file as 'DISABLED' and changes the file to a .txt file

        Parameters
        ----------
        file: :class:`str`
            The file path to the file we are working with

        filePrefix: :class:`str`
            Prefix name we want to add in front of the file name :raw-html:`<br />` :raw-html:`<br />`

            **Default**: "DISABLED_RSFixBackup\_"
        """

        baseName = os.path.basename(file)
        baseName = FileService.changeExt(baseName, TxtExt)

        backupFile = os.path.join(os.path.dirname(file), filePrefix) + baseName
        FileService.rename(file, backupFile)

    @classmethod
    def parseOSPath(cls, path: str):
        """
        Retrieves a normalized file path from a string

        Parameters
        ----------
        path: :class:`str`
            The string containing some sort of file path
        """

        result = ntpath.normpath(path)
        result = cls.ntPathToPosix(result)
        return result

    @classmethod
    def ntPathToPosix(cls, path: str) -> str:
        """
        Converts a file path from the `ntpath <https://opensource.apple.com/source/python/python-3/python/Lib/ntpath.py.auto.html>`_ library to a file path for the `os <https://docs.python.org/3/library/os.html>`_ library

        .. note::
            The character for the folder paths (``/`` or ``\\``) used in both libraries may be different depending on the OS

        Parameters
        ----------
        path: :class:`str`
            The file path we are working that is generated from the 'ntpath' library

        Returns
        -------
        :class:`str`
            The file path generated by the 'os' library
        """

        return path.replace(ntpath.sep, os.sep)
    
    @classmethod
    def absPathOfRelPath(cls, dstPath: str, relFolder: str) -> str:
        """
        Retrieves the absolute path of the relative path of a file with respect to a certain folder

        Parameters
        ----------
        dstPath: :class:`str`
            The target file path we are working with

        relFolder: :class:`str`
            The folder that the target file path is relative to

        Returns
        -------
        :class:`str`
            The absolute path for the target file
        """

        relFolder = os.path.abspath(relFolder)
        result = dstPath
        if (not os.path.isabs(result)):
            result = os.path.join(relFolder, result)
            result = cls.parseOSPath(result)

        return result
    
    @classmethod
    def getRelPath(cls, path: str, start: str) -> str:
        """
        Tries to get the relative path of a file/folder relative to another folder, if possible.

        If it is not possible to get the relative path, will return back the original file path

        .. note::
            An example where it would not be possible to get the relative path would be:
            
            * If the file is located in one mount (eg. C:/ drive) and the folder is located in another mount (eg. D:/ drive)

        Parameters
        ----------
        path: :class:`str`
            The path to the target file/folder we are working with

        start: :class:`str`
            The path that the target file/folder is relative to

        Returns
        -------
        :class:`str`
            Either the relative path or the original path if not possible to get the relative paths
        """

        result = path
        try:
            result = os.path.relpath(path, start)

        # if the path is in another mount than 'start'
        except ValueError:
            pass

        return result
    
    # read(file, fileCode, postProcessor): Tries to read a file using different encodings
    @classmethod
    def read(cls, file: str, fileCode: str, postProcessor: Callable[[TextIoWrapper], Any]) -> Any:
        """
        Tries to read a file using different file encodings

        Will interact with the file using the following order of encodings:

        #. utf-8 
        #. latin1

        Parameters
        ----------
        file: :class:`str`
            The file we are trying to read from

        fileCode: :class:`str`
            What `file mode <https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files>`_ to interact with the file (eg. r, rb, r+, etc...)

        postProcessor: Callable[[`TextIoWrapper`_], Any]
            A function used to process the file pointer of the opened file

        Returns
        -------
        Any
            The result after processing the file pointer of the opened file
        """

        for encoding in ReadEncodings:
            try:
                with open(file, fileCode, encoding = encoding) as f:
                    return postProcessor(f)
            except UnicodeDecodeError:
                pass

    @classmethod
    def getPath(cls, path: Optional[str]) -> str:
        if (path is None):
            return DefaultPath
        return path


class Logger():
    """
    Class for pretty printing output to display on the console

    Parameters
    ----------
    prefix: :class:`str`
        line that is printed before any message is printed out :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ""

    logTxt: :class:`bool`
        Whether to log all the printed messages into a .txt file once the fix is done :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``False``

    verbose: :class:`bool`
        Whether to print out output :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``True``

    Attributes
    ----------
    _prefix: :class:`str`
        line that is printed before any message is printed out

    _headingTxtLen: :class:`int`
        The number of characters used for the name of the opening heading

    _headingSideLen: :class:`int`
        The number of characters used to make side border of an opening/closing heading

    _headingChar: :class:`str`
        The character used to make the border of an opening/closing heading

    includePrefix: :class:`bool`
        Whether to include the prefix string when printing out a message

    verbose: :class:`bool`
        Whether to print out output

    logTxt: :class:`bool`
        Whether to log all the printed messages into a .txt file once the fix is done

    _loggedTxt: :class:`str`
        The text that will be logged into a .txt file
    """

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
        """
        The line of text that is printed before any message is printed out

        :getter: Returns such a prefix
        :setter: Sets up such a prefix for the logger
        :type: :class:`str`
        """
        return self._prefix
    
    @prefix.setter
    def prefix(self, newPrefix):
        self._prefix = newPrefix
        self._currentPrefixTxt = ""

    @property
    def loggedTxt(self):
        """
        The text to be logged into a .txt file

        :getter: Returns such a prefix
        :type: :class:`str`
        """
        return self._loggedTxt

    def _setDefaultHeadingAtts(self):
        """
        Sets the default attributes for printing out a header line
        """

        self._headingTxtLen = 0
        self._headingSideLen = self.DefaultHeadingSideLen
        self._headingChar = self.DefaultHeadingChar

    def _addLogTxt(self, txt: str):
        """
        Appends the text to the logged output to be printed to a .txt file

        Parameters
        ----------
        txt: :class:`str`
            The text to be added onto the logged output
        """

        if (self.logTxt):
            self._loggedTxt += f"{txt}\n"

    def getStr(self, message: str):
        """
        Retrieves the string to be printed out by the logger

        Parameters
        ----------
        message: :class:`str`
            The message we want to print out

        Returns
        -------
        :class:`str`
            The transformed text that the logger prints out
        """

        return f"# {self._prefix} --> {message}"

    def log(self, message: str):
        """
        Regularly prints text onto the console

        Parameters
        ----------
        message: :class:`str`
            The message we want to print out
        """

        if (not self.verbose):
            return

        if (self.includePrefix):
            message = self.getStr(message)

        self._addLogTxt(message)
        self._currentPrefixTxt += message
        print(message)

    def split(self):
        """
        Prints out a new line
        """

        if (self._currentPrefixTxt):
            self.log("\n")

    def space(self):
        """
        Prints out a space
        """
        self.log("")

    def openHeading(self, txt: str, sideLen: int = DefaultHeadingSideLen, headingChar = DefaultHeadingChar):
        """
        Prints out an opening heading

        Parameters
        ----------
        txt: :class:`str`
            The message we want to print out

        sideLen: :class:`int`
            How many characters we want for the side border of the heading :raw-html:`<br />` :raw-html:`<br />`

            **Default**: 2

        headingChar: :class:`str`
            The character used to print the side border of the heading :raw-html:`<br />` :raw-html:`<br />`

            **Default**: "="
        """

        self._headingTxtLen = len(txt)
        self._headingSideLen = sideLen
        self._headingChar = headingChar
        
        side = headingChar * sideLen
        self.log(f"{side} {txt} {side}")

    def closeHeading(self):
        """
        Prints out a closing heading that corresponds to a previous opening heading printed
        """

        side = self._headingChar * self._headingSideLen
        mid = self._headingChar * (self._headingTxtLen + 2)
        self.log(f"{side}{mid}{side}")

        self._setDefaultHeadingAtts()

    @classmethod
    def getBulletStr(self, txt: str) -> str:
        """
        Creates the string for an item in an unordered list

        Parameters
        ----------
        txt: :class:`str`
            The message we want to print out

        Returns
        -------
        :class:`str`
            The text formatted as an item in an unordered list
        """
        return f"- {txt}"
    
    @classmethod
    def getNumberedStr(self, txt: str, num: int) -> str:
        """
        Creates the string for an ordered list

        Parameters
        ----------
        txt: :class:`str`
            The message we want to print out

        num: :class:`str`
            The number we want to print out before the text for the ordered list

        Returns
        -------
        :class:`str`
            The text formatted as an item in an ordered list
        """
        return f"{num}. {txt}"

    def bulletPoint(self, txt: str):
        """
        Prints out an item in an unordered list

        Parameters
        ----------
        txt: :class:`str`
            The message we want to print out
        """
        self.log(self.getBulletStr(txt))

    def list(self, lst: List[str], transform: Optional[Callable[[str], str]] = None):
        """
        Prints out an ordered list

        Parameters
        ----------
        lst: List[:class:`str`]
            The list of messages we want to print out

        transform: Optional[Callable[[:class:`str`], :class:`str`]]
            A function used to do any processing on each message in the list of messages

            If this parameter is ``None``, then the list of message will not go through any type of processing :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ``None``
        """

        if (transform is None):
            transform = lambda txt: txt

        lstLen = len(lst)
        for i in range(lstLen):
            newTxt = transform(lst[i])
            self.log(self.getNumberedStr(newTxt, i + 1))

    def box(self, message: str, header: str):
        """
        Prints the message to be sandwiched by the text defined in the argument, ``header``

        Parameters
        ----------
        message: :class:`str`
            The message we want to print out

        header: :class:`str`
            The string that we want to sandwich our message against
        """

        self.log(header)

        messageList = message.split("\n")
        for messagePart in messageList:
            self.log(messagePart)

        self.log(header)

    def error(self, message: str):
        """
        Prints an error message

        Parameters
        ----------
        message: :class:`str`
            The message we want to print out
        """

        self.space()
        prevVerbose = self.verbose
        self.verbose = True

        self.box(message, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        self.space()
        self.verbose = prevVerbose

    def note(self, message: str):
        """
        Prints an important note that the user should take note of

        Parameters
        ----------
        message: :class:`str`
            The message we want to print out
        """

        self.space()
        self.box(f"Note: {message}", "*****************************")

    @classmethod
    def getWarnStr(self, exception: Error) -> str:
        """
        Retrieves the string for a warning

        Parameters
        ----------
        exception: :class:`Error`
            The warning we want to handle

        Returns
        -------
        :class:`str`
            The warning string
        """
        
        return f"{type(exception).__name__}: {exception.warn()}"
    
    def warn(self, exception: Error):
        """
        Prints a warning

        Parameters
        ----------
        exception: :class:`Error`
            The warning we want to handle
        """
        self.error(self.getWarnStr(exception))

    def handleException(self, exception: BaseException):
        """
        Prints the message for an error

        Parameters
        ----------
        exception: :class:`BaseException`
            The error we want to handle
        """

        message = f"\n{type(exception).__name__}: {exception}\n\n{traceback.format_exc()}"
        self.error(message)

    def input(self, desc: str) -> str:
        """
        Handles user input from the console

        Parameters
        ----------
        desc: :class:`str`
            The question/description being asked to the user for input

        Returns
        -------
        :class:`str`
            The resultant input the user entered
        """

        if (self.includePrefix):
            desc = self.getStr(desc)

        self._addLogTxt(desc)
        result = input(desc)
        self._addLogTxt(f"Input: {result}")

        return result

    def waitExit(self):
        """
        Prints the message used when the script finishes running
        """

        prevIncludePrefix = self.includePrefix
        self.includePrefix = False
        self.input("\n== Press ENTER to exit ==")
        self.includePrefix = prevIncludePrefix 


# our model objects in MVC
class Model():
    """
    Generic class used for any data models in the fix

    Parameters
    ----------
    logger: Optional[:class:`Logger`]
        The logger used to print messages to the console :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``None``

    Attributes
    ----------
    logger: Optional[:class:`Logger`]
        The logger used to print messages to the console
    """
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger

    def print(self, funcName: str, *args, **kwargs):
        """
        Prints out output

        Parameters
        ----------
        funcName: :class:`str`
            The name of the function in the logger for printing out the output

        \*args: List[:class:`str`]
            Arguments to pass to the function in the logger

        \*\*kwargs: Dict[:class:`str`, Any]
            Keyword arguments to pass to the function in the logger

        Returns
        -------
        :class:`Any`
            The return value from running the corresponding function in the logger 
        """

        if (self.logger is not None):
            func = getattr(self.logger, funcName)
            return func(*args, **kwargs)


# Needed data model to inject into the .ini file
class RemapBlendModel():
    """
    Contains data for fixing a particular resource in a .ini file

    Parameters
    ----------
    iniFolderPath: :class:`str`
        The folder path to where the .ini file of the resource is located

    fixedBlendName: :class:`str`
        The new name of the resource once all the Blend.buf files for the resource has been fixed

    fixedBlendPaths: Dict[:class:`int`, :class:`str`]
        The file paths to the fixed RemapBlend.buf files for the resource
        :raw-html:`<br />` :raw-html:`<br />`
        The keys are the indices that the Blend.buf file appears in the :class:`IfTemplate` for some resource

    origBlendName: Optional[:class:`str`]
        The original name of the resource in the .ini file :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``None``

    origBlendPaths: Optional[Dict[:class:`int`, :class:`str`]]
        The file paths to the Blend.buf files for the resource
        :raw-html:`<br />` :raw-html:`<br />`
        The keys are the indices that the Blend.buf file appears in the :class:`IfTemplate` for some resource :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``None``

    Attributes
    ----------
    iniFolderPath: :class:`str`
        The folder path to where the .ini file of the resource is located

    fixedBlendName: :class:`str`
        The new name of the resource once all the Blend.buf files for the resource has been fixed

    fixedBlendPaths: Dict[:class:`int`, :class:`str`]
        The file paths to the fixed RemapBlend.buf files for the resource
        :raw-html:`<br />` :raw-html:`<br />`
        The keys are the indices that the Blend.buf file appears in the :class:`IfTemplate` for the resource

    origBlendName: Optional[:class:`str`]
        The original name of the resource in the .ini file

    origBlendPaths: Optional[Dict[:class:`int`, :class:`str`]]
        The file paths to the Blend.buf files for the resource :raw-html:`<br />` :raw-html:`<br />`

        The keys are the indices that the Blend.buf file appears in the :class:`IfTemplate` for the resource

    fullPaths: Dict[:class:`int`, :class:`str`]
        The absolute paths to the fixed RemapBlend.buf files for the resource :raw-html:`<br />` :raw-html:`<br />`

        The keys are the indices that the Blend.buf file appears in the :class:`IfTemplate` for the resource

    origFullPaths: Dict[:class:`int`, :class:`str`]
        The absolute paths to the Blend.buf files for the resource :raw-html:`<br />` :raw-html:`<br />`

        The keys are the indices that the Blend.buf file appears in the :class:`IfTemplate` for the resource
    """

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

        if (self.origBlendPaths is not None):
            for partIndex in self.origBlendPaths:
                path = self.origBlendPaths[partIndex]
                self.origFullPaths[partIndex] = FileService.absPathOfRelPath(path, iniFolderPath)


# IfTemplate: Data class for the if..else template of the .ini file
class IfTemplate():
    """
    Data for storing information about a `section`_ in a .ini file

    :raw-html:`<br />`

    .. note::
        Assuming every `if/else` clause must be on its own line, we have that an :class:`IfTemplate` have a form looking similar to this:

        .. code-block:: ini
            :linenos:
            :emphasize-lines: 1,2,5,7,12,16,17

            ...(does stuff)...
            ...(does stuff)...
            if ...(bool)...
                if ...(bool)...
                    ...(does stuff)...
                else if ...(bool)...
                    ...(does stuff)...
                endif
            else ...(bool)...
                if ...(bool)...
                    if ...(bool)...
                        ...(does stuff)...
                    endif
                endif
            endif
            ...(does stuff)...
            ...(does stuff)...

        We split the above structure into parts where each part is either:

        #. **An If Part**: a single line containing the keywords "if", "else" or "endif" :raw-html:`<br />` **OR** :raw-html:`<br />`
        #. **A Content Part**: a group of lines that *"does stuff"*

        **Note that:** an :class:`ifTemplate` does not need to contain any parts containing the keywords "if", "else" or "endif". This case covers the scenario
        when the user does not use if..else statements for a particular `section`_
        
        Based on the above assumptions, we can assume that every ``[section]`` in a .ini file contains this :class:`IfTemplate`

    :raw-html:`<br />`

    .. container:: operations

        **Supported Operations:**

        .. describe:: for element in x

            Iterates over all the parts of the :class:`IfTemplate`, ``x``

        .. describe:: x[num]

            Retrieves the part from the :class:`IfTemplate`, ``x``, at index ``num``

        .. describe:: x[num] = newPart

            Sets the part at index ``num`` of the :class:`IfTemplate`, ``x``, to have the value of ``newPart``

    :raw-html:`<br />`

    Parameters
    ----------
    parts: List[Union[:class:`str`, Dict[:class:`str`, Any]]]
        The individual parts of how we divided an :class:`IfTemplate` described above

    calledSubCommands: Optional[Dict[:class:`int`, :class:`str`]]
        Any other sections that this :class:`IfTemplate` references
        :raw-html:`<br />` :raw-html:`<br />`
        The keys are the indices to the part in the :class:`IfTemplate` that the section is called :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``None``

    Attributes
    ----------
    parts: List[Union[:class:`str`, Dict[:class:`str`, Any]]]
        The individual parts of how we divided an :class:`IfTemplate` described above

    calledSubCommands: Optional[Dict[:class:`int`, :class:`str`]]
        Any other sections that this :class:`IfTemplate` references
        :raw-html:`<br />` :raw-html:`<br />`
        The keys are the indices to the part in the :class:`IfTemplate` that the section is called
    """

    def __init__(self, parts: List[Union[str, Dict[str, Any]]], calledSubCommands: Optional[Dict[int, str]] = None):
        self.parts = parts
        self.calledSubCommands = calledSubCommands

        if (calledSubCommands is None):
            self.calledSubCommands = {}

    def __iter__(self):
        return self.parts.__iter__()
    
    def __getitem__(self, key: int) -> Union[str, Dict[str, Any]]:
        return self.parts[key]
    
    def __setitem__(self, key: int, value: Union[str, Dict[str, Any]]):
        self.parts[key] = value

    def add(self, part: Union[str, Dict[str, Any]]):
        """
        Adds a part to the :class:`ifTemplate`

        Parameters
        ----------
        part: Union[:class:`str`, Dict[:class:`str`, Any]]
            The part to add to the :class:`IfTemplate`
        """
        self.parts.append(part)

    # find(pred, postProcessor): Searches each part in the if template based on 'pred'
    def find(self, pred: Optional[Callable[[Union[str, Dict[str, Any]]], bool]] = None, postProcessor: Optional[Callable[[Union[str, Dict[str, Any]]], Any]] = None) -> Dict[int, Any]:
        """
        Searches the :class:`IfTemplate` for parts that meet a certain condition

        Parameters
        ----------
        pred: Optional[Callable[[Union[:class:`str`, Dict[:class:`str`, Any]]], :class:`bool`]]
            The predicate used to filter the parts :raw-html:`<br />` :raw-html:`<br />`

            If this value is ``None``, then this function will return all the parts :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ``None``

        postProcessor: Optional[Callable[[Union[:class:`str`, Dict[str, Any]]], Any]]
            A function that performs any post-processing on the found part that meets the required condition :raw-html:`<br />` :raw-html:`<br />`
        
            **Default**: ``None``
        """

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
class IniFile(Model):
    """
    This class inherits from :class:`Model`

    Class for handling .ini files

    :raw-html:`<br />`

    .. note::
        We analyse the .ini file using Regex which is **NOT** the right way to do things
        since the modified .ini language that GIMI interprets is a **CFG** (context free grammer) and **NOT** a regular language.
   
        But since we are lazy and don't want make our own compiler with tokenizers, parsing algorithms (eg. SLR(1)), type checking, etc...
        this module should handle regular cases of .ini files generated using existing scripts (assuming the user does not do anything funny...)

    :raw-html:`<br />`

    Parameters
    ----------
    file: Optional[:class:`str`]
        The file path to the .ini file :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``None``

    logger: Optional[:class:`Logger`]
        The logger to print messages if necessary

    txt: :class:`str`
        Used as the text content of the .ini file if :attr:`IniFile.file` is set to ``None`` :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ""

    mustBeRaiden: :class:`bool`
        Whether the .ini file has to be used for a Raiden mod :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``True``

    Attributes
    ----------
    file: :class:`str`
        The file path to the .ini file

    _parser: `ConfigParser`_
        Parser used to parse very basic cases in a .ini file

    _fileLines: List[:class:`str`]
        The file lines read from the .ini file

    _fileLinesRead: :class:`bool`
        Whether the file for the .ini file has been read

    _isRaidenFixed: :class:`bool`
        Whether the .ini file has already been fixed

    _isRaidenIni: :class:`bool`
        Whether the .ini file is used for a Raiden mod

    mustBeRaiden: :class:`bool`
        Whether the .ini file has to be used for a Raiden mod :raw-html:`<br />` :raw-html:`<br />`

    _textureOverrideBlendRoot: Optional[:class:`str`]
        The name for the `section`_ containing the keywords: ``[.*TextureOverride.*Blend.*]``

    _sectionIfTemplates: Dict[:class:`str`, :class:`IfTemplate`]
        All the `sections`_ in the .ini file that can be parsed into an :class:`IfTemplate`

        For more info see :class:`IfTemplate`

        .. warning::
            The modified .ini language that GIMI uses introduces keywords that can be used before the key of a key-value pair :raw-html:`<br />`

            *eg. defining constants*

            .. code-block:: ini
                :linenos:

                [Constants]
                global persist $swapvar = 0
                global persist $swapscarf = 0
                global $active
                global $creditinfo = 0

            :raw-html:`<br />`

            `Sections`_ containing this type of pattern will not be parsed. But generally, these sections are irrelevant to fixing the Raiden Boss

    _resourceBlends: Dict[:class:`str`, :class:`IfTemplate`]
        `Sections`_ that are linked to 1 or more Blend.buf files.

        The keys are the name of the sections.

    _blendCommands: Dict[:class:`str`, :class:`IfTemplate`]
        All the `sections`_ that use some ``[Resource.*Blend.*]`` section. :raw-html:`<br />` :raw-html:`<br />`

        The keys are the name of the sections.

    _blendCommandsRemapNames: Dict[:class`str`, :class:`str`]
        The new names for the `sections`_ that use some ``[Resource.*Blend.*]`` section that will be used in the fix. :raw-html:`<br />` :raw-html:`<br />`

        The keys are the original names of the `sections`_ in the .ini file

    _blendCommandsTuples: List[Tuple[:class:`str`, :class:`IfTemplate`]]
        All the `sections`_ that use some ``[Resource.*Blend.*]`` section while maitaining the order that sections have been called

        .. note::
            This attribute is the same as :attr:`IniFile._blendCommands` except that the order that `sections`_ are called in the call stack is preserved

    _resourceCommands: Dict[:class:`str`, :class:`IfTemplate`]
        All the related `sections`_ to the ``[Resource.*Blend.*]`` sections that are used by `sections`_ related to the ``[TextureOverride.*Blend.*]`` sections.
        The keys are the name of the `sections`_.

    _resourceCommandsRemapNames: Dict[:class:`str`, :class:`str`]
        The new names to be used in the fix for all the related `sections`_ to the ``[Resource.*Blend.*]`` `sections`_ that are used by `sections`_ related to ``[TextureOverride.*Blend.*]`` `sections`_.

        The keys are the original names of the `sections`_ in the .ini file

    _resouceCommandsTuples: List[Tuple[:class:`str`, :class:`IfTemplate`]]
       All the related `sections`_ to the ``[Resource.*Blend.*]`` `sections`_ that are used by `sections`_ related to ``[TextureOverride.*Blend.*]`` `sections`_ 
       while maitaining the order that the `sections`_ have been called

        .. note::
            This attribute is the same as :attr:`IniFile._resourceCommands` except that the order that `sections`_ are called in the call stack is preserved

    remapBlendModelsDict: Dict[:class:`str`, :class:`RemapBlendModel`]
        The data for the ``[Resource.*RemapBlend.*]`` `sections`_ used in the fix

        The keys are the original names of the resource with the pattern ``[Resource.*Blend.*]``

    remapBlendModels: List[:class:`RemapBlendModel`]
        The data for the ``[Resource.*RemapBlend.*]`` `sections`_ used in the fix

        .. note::
            This attribute is the same as the values of :attr:`IniFile.remapBlendModelsDict` by calling: 
            
            .. code-block:: python
                :linenos:

                list(remapBlendModelsDict.values())
    """


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

    def __init__(self, file: Optional[str] = None, logger: Optional[Logger] = None, txt: str = "", mustBeRaiden: bool = True):
        super().__init__(logger = logger)
        self.file = file
        self._parser = configparser.ConfigParser()

        self._fileLines = []
        self._fileLinesRead = False
        self._setupFileLines(fileTxt = txt)

        self._isRaidenFixed = False
        self._isRaidenIni = False
        self.mustBeRaiden = mustBeRaiden

        self._textureOverrideBlendRoot: Optional[str] = None
        self._sectionIfTemplates: Dict[str, IfTemplate] = {}
        self._resourceBlends: Dict[str, IfTemplate] = {}

        self._blendCommands: Dict[str, IfTemplate] = {}
        self._blendCommandsRemapNames: Dict[str, str] = {}
        self._blendCommandsTuples: List[Tuple[str, IfTemplate]] = []

        self._resourceCommands: Dict[str, IfTemplate] = {}
        self._resourceCommandsRemapNames:Dict[str, str] = {}
        self._resourceCommandsTuples: List[Tuple[str, IfTemplate]] = []

        self.remapBlendModelsDict: Dict[str, RemapBlendModel] = {}
        self.remapBlendModels: List[RemapBlendModel] = []

    @property
    def isRaidenFixed(self):
        """
        Whether the .ini file has already been fixed

        :getter: Returns whether the .ini file has already been fixed
        :type: :class:`bool`
        """

        return self._isRaidenFixed
    
    @property
    def isRaidenIni(self):
        """
        Whether the .ini file is a for a Raiden mod

        :getter: Returns whether the .ini file is a for a Raiden mod
        :type: :class:`bool`
        """

        return self._isRaidenIni

    def clearRead(self):
        """
        Clears all the saved text read in from the .ini file
        """

        self._fileLines = []
        self._fileLinesRead = False
        self._isRaidenFixed = False

    def read(self) -> str:
        """
        Reads the .ini file

        Returns
        -------
        :class:`str`
            The text content of the .ini file
        """

        result = ""
        result = FileService.read(self.file, "r", lambda filePtr: filePtr.read())
        return result
    
    def write(self) -> str:
        """
        Writes back into the .ini files based off the content in :attr:`IniFile._fileLines`

        Returns
        -------
        :class:`str`
            The text that is written to the .ini file
        """

        txtToWrite = "".join(self._fileLines)

        if (self.file is None):
            return txtToWrite

        with open(self.file, "w", encoding = IniFileEncoding) as f:
            f.write(txtToWrite)

        return txtToWrite

    def _setupFileLines(self, fileTxt: str = ""):
        if (self.file is not None):
            return
        
        self._fileLines = fileTxt.split("\n")

        fileLinesLen = len(self._fileLines)
        for i in range(fileLinesLen):
            if (i < fileLinesLen - 1):
                self._fileLines[i] += "\n"

        self._fileLinesRead = True


    def getFileLines(self) -> List[str]:
        """
        Reads each line in the .ini file

        Returns
        -------
        List[:class:`str`]
            All the lines of the .ini file
        """

        self._fileLines = FileService.read(self.file, "r", lambda filePtr: filePtr.readlines())
        self._fileLinesRead = True
        return self._fileLines

    def _readLines(func):
        """
        Decorator to read all the lines in the .ini file first before running a certain function

        All the file lines will be saved in :attr:`IniFile._fileLines`

        Examples
        --------
        .. code-block:: python
            :linenos:

            @_readLines
            def printLines(self):
                for line in self._fileLines:
                    print(f"LINE: {line}")
        """

        def readLinesWrapper(self, *args, **kwargs):
            if (not self._fileLinesRead):
                self.getFileLines()
            return func(self, *args, **kwargs)
        return readLinesWrapper
    
    def checkRaidenIni(self, mustBeRaiden: Optional[bool] = None) -> bool:
        """
        Reads the entire .ini file and checks whether the .ini file is a Raiden mod that needs to be fixed

        .. note::
            If the .ini file has already been parsed (eg. calling :meth:`IniFile.checkRaidenIni` or :meth:`IniFile.parse`), then

            you only need to read the :attr:`IniFile._isRaidenIni`

        Parameters
        ----------
        mustBeRaiden: Optional[:class:`bool`]
            Whether the .ini file being checked has to be a Raiden mod

        Returns
        -------
        :class:`bool`
            Whether the .ini file is a .ini file that needs to be fixed
        """

        postProcessor = lambda startInd, endInd, fileLines, sectionName, srcTxt: sectionName
        textureOverridePattern = self._textureOverrideRaidenBlendPattern
        if ((mustBeRaiden is not None and not mustBeRaiden) or (mustBeRaiden is None and not self.mustBeRaiden)):
            textureOverridePattern = self._textureOverrideBlendPattern

        textureOverrideBlendSections = self.getSectionOptions(textureOverridePattern , postProcessor = postProcessor)

        self._isRaidenIni = bool(textureOverrideBlendSections)
        if (self._isRaidenIni):
            self._textureOverrideBlendRoot = DictTools.getFirstKey(textureOverrideBlendSections)

        return self._isRaidenIni
    
    def _checkRaidenIni(self, line: str):
        """
        Checks if a line of text contains the keywords to identify whether the .ini file is a Raiden mod :raw-html:`<br />` :raw-html:`<br />`

        * If :attr:`IniFile.mustBeRaiden` is ``True``, then will see if the line matches with the regex, ``[.*TextureOverride.*(Raiden|Shogun).*Blend.*]``
        * Otherwise, will see if the line matches with the regex, ``[.*TextureOverride.*Blend.*]`` 

        Parameters
        ----------
        line: :class:`str`
            The text to check
        """

        if (self._textureOverrideBlendRoot is None and 
            ((self.mustBeRaiden and self._textureOverrideRaidenBlendPattern.match(line)) or 
             (not self.mustBeRaiden and self._textureOverrideBlendPattern.match(line)))):
            self._textureOverrideBlendRoot = self._getSectionName(line)
            self._isRaidenIni = True

    def _checkRaidenFixed(self, line: str):
        """
        Checks if a line of text matches the regex, ``[.*TextureOverride.*RemapBlend.*]`` ,to identify whether the .ini file has been fixed

        Parameters
        ----------
        line: :class:`str`
            The line of text to check
        """

        if (not self._isRaidenFixed and self._fixedTextureOverrideBlendPattern.match(line)):
            self._isRaidenFixed = True

    def _parseSection(self, sectionName: str, srcTxt: str, save: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, str]]:
        """
        Regularly parses the key-value pairs of a certain `section`_

        The function parses uses `ConfigParser`_ to parse the `section`_.

        Parameters
        ----------
        sectionName: :class:`str`
            The name of the `section`_

        srcTxt: :class:`str`
            The text containing the entire `section`_

        save: Optional[Dict[:class:`str`, Any]]
            Place to save the parsed result for the `section`_  :raw-html:`<br />` :raw-html:`<br />`

            The result for the parsed `section`_ will be saved as a value in the dictionary while section's name will be used in the key for the dictionary :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ``None``

        Returns
        -------
        Optional[Dict[:class:`str`, :class:`str`]]
            The result from parsing the `section`_

            .. note:: 
                If `ConfigParser`_ is unable to parse the section, then ``None`` is returned
        """

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
    
    def _getSectionName(self, line: str) -> str:
        currentSectionName = line.strip().replace("]", "")
        currentSectionName = currentSectionName.replace("[", "")
        return currentSectionName

    # retrieves the key-value pairs of a section in the .ini file. Manually parsed the file since ConfigParser
    #   errors out on conditional statements in .ini file for mods. Could later inherit from the parser (RawConfigParser) 
    #   to custom deal with conditionals
    @_readLines
    def getSectionOptions(self, section: Union[str, Pattern, Callable[[str], bool]], postProcessor: Optional[Callable[[int, int, List[str], str, str], Any]] = None) -> Dict[str, Any]:
        """
        Reads the entire .ini file for a certain type of `section`_

        Parameters
        ----------
        section: Union[:class:`str`, `Pattern`_, Callable[[:class:`str`], :class:`bool`]]
            The type of section to find

            * If this argument is a :class:`str`, then will check if the line in the .ini file exactly matches the argument
            * If this argument is a `Pattern`_, then will check if the line in the .ini file matches the specified Regex pattern
            * If this argument is a function, then will check if the line in the .ini file passed as an argument for the function will make the function return ``True``

        postProcessor: Optional[Callable[[:class:`int`, :class:`int`, List[:class:`str`], :class:`str`, :class:`str`], Any]]
            Post processor used when a type of `section`_ has been found

            The order of arguments passed into the post processor will be:

            #. The starting line index of the `section`_ in the .ini file
            #. The ending line index of the `section`_ in the .ini file
            #. All the file lines read from the .ini file
            #. The name of the `section`_ found
            #. The entire text for the `section`_ :raw-html:`<br />` :raw-html:`<br />`

            **Default**: `None`

        Returns
        -------
        Dict[:class:`str`, Any]
            The resultant `sections`_ found

            The keys are the names of the `sections`_ found and the values are the content for the `section`_
        """

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
            self._checkRaidenIni(line)

            if (sectionFilter(line)):
                currentSectionToParse = f"{line}"
                currentSectionName = self._getSectionName(currentSectionToParse)
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

    def _removeSection(self, startInd: int, endInd: int, fileLines: List[str], sectionName: str, srcTxt: str) -> Tuple[int, int]:
        """
        Retrieves the starting line index and ending line index of where to remove a certain `section`_ from the read lines of the .ini file

        Parameters
        ----------
        startInd: :class:`int`
            The starting line index of the `section`_

        endInd: :class:`int`
            The ending line index of the `section`_

        fileLines: List[:class:`str`]
            All the file lines read from the .ini file

        sectionName: :class:`str`
            The name of the `section`_

        srcTxt: :class:`str`
            The text content of the `section`_

        Returns
        -------
        Tuple[:class:`int`, :class:`int`]
            The starting line index and the ending line index of the `section`_ to remove
        """

        if (endInd >= len(fileLines)):
            return (startInd, endInd)
        return (startInd, endInd + 1)
    
    def removeSectionOptions(self, section: Union[str, Pattern, Callable[[str], bool]]):
        """
        Removes a certain type of `section`_ from the .ini file

        Parameters
        ----------
        section: Union[:class:`str`, `Pattern`_, Callable[[:class:`str`], :class:`bool`]]
            The type of `section`_ to remove
        """

        rangesToRemove = self.getSectionOptions(section, postProcessor = self._removeSection)

        for sectionName in rangesToRemove:
            range = rangesToRemove[sectionName]
            startInd = range[0]
            endInd = range[1]

            self._fileLines[startInd:endInd] =  [0] * (endInd - startInd)

        self._fileLines = list(filter(lambda line: line != 0, self._fileLines))

    def _processIfTemplate(self, startInd: int, endInd: int, fileLines: List[str], sectionName: str, srcTxt: str) -> IfTemplate:
        """
        Parses a `section`_ in the .ini file as an :class:`IfTemplate`

        .. note::
            See :class:`IfTemplate` to see how we define an 'IfTemplate'

        Parameters
        ----------
        startInd: :class:`int`
            The starting line index of the `section`_

        endInd: :class:`int`
            The ending line index of the `section`_

        fileLines: List[:class:`str`]
            All the file lines read from the .ini file

        sectionName: :class:`str`
            The name of the `section`_

        srcTxt: :class:`str`
            The text content of the `section`_

        Returns
        -------
        :class:`IfTemplate`
            The generated :class:`IfTemplate` from the `section`_
        """

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
        """
        Retrieves the index number of a resource created by GIMI's ``genshin_merge_mods.py`` script

        Examples
        --------
        >>> IniFile.getMergedResourceIndex("ResourceCuteLittleEiBlend.8")
        8

        Parameters
        ----------
        mergedResourceName: :class:`str`
            The name of the `section`_

        Returns
        -------
        :class:`str`
            The index for the resource `section`_
        """
        
        return mergedResourceName.rsplit(".", 1)[-1]
    
    def _getResourceSortKey(self, resourceTuple: Tuple[str, Any]) -> int:
        """
        Retrieves the index number of a resource created by GIMI's ``genshin_merge_mods.py`` script as an integer

        .. note::
            See :meth:`IniFile.getMergedResourceIndex` for more info

        Parameters
        ----------
        resourceTuple: Tuple[:class:`str`, Any]
            The name of the resource section and its content

        Returns
        -------
        :class:`int`
            The index for the resource section
        """

        result = -1
        try:
            result = int(self.getMergedResourceIndex(resourceTuple[0]))
        except:
            pass

        return result

    # Disabling the OLD ini
    def disIni(self):
        """
        Disables the .ini file

        .. note::
            For more info, see :meth:`FileService.disableFile`
        """

        FileService.disableFile(self.file)

    @classmethod
    def getFixedBlendFile(cls, blendFile: str) -> str:
        """
        Retrieves the file path for the fixed RemapBlend.buf file

        Parameters
        ----------
        blendFile: :class:`str`
            The file path to the original Blend.buf file

        Returns
        -------
        :class:`str`
            The file path of the fixed RemapBlend.buf file
        """

        blendFile = blendFile.rsplit(".", 1)[0]
        blendFolder = os.path.dirname(blendFile)
        blendBaseName = os.path.basename(blendFile)
        
        return os.path.join(blendFolder, f"{cls.getRemapName(blendBaseName)}.buf")

    @classmethod
    def getFixHeader(cls) -> str:
        """
        Retrieves the header text used to identify a code section has been changed by this fix
        in the .ini file        
        """

        return cls._fixHeader
    
    @classmethod
    def getFixFooter(cls) -> str:
        """
        Retrieves the footer text used to identify a code section has been changed by this fix
        in the .ini file  
        """

        return f"\n\n{cls._fixFooter}"

    def _addFixBoilerPlate(func):
        """
        Decorator used to add the boilerplate code to identify a code section has been changed by this fix in the .ini file

        Examples
        --------
        .. code-block:: python
            :linenos:

            @_addFixBoilerPlate
            def helloWorld(self) -> str:
                return "Hello World"
        """

        def addFixBoilerPlateWrapper(self, *args, **kwargs):
            addFix = self.getFixHeader()
            addFix += self.Credit
            addFix += func(self, *args, **kwargs)
            addFix += self.getFixFooter()

            return addFix
        return addFixBoilerPlateWrapper
    
    @classmethod
    def getResourceName(cls, name: str) -> str:
        """
        Makes the name of a `section`_ to be used for the resource `sections`_ of a .ini file

        Examples
        --------
        >>> IniFile.getResourceName("CuteLittleEi")
        "ResourceCuteLittleEi"

        Parameters
        ----------
        name: :class:`str`
            The name of the `section`_

        Returns
        -------
        :class:`str`
            The name of the `section`_ as a resource in a .ini file
        """

        return f"{cls.Resource}{name}"
    
    @classmethod
    def removeResourceName(cls, name: str) -> str:
        """
        Removes the 'Resource' prefix from a section's name

        Examples
        --------
        >>> IniFile.removeResourceName("ResourceCuteLittleEi")
        "CuteLittleEi"

        

        >>> IniFile.removeResourceName("LittleMissGanyu")
        "LittleMissGanyu"

        Parameters
        ----------
        name: :class:`str`
            The name of the `section`_

        Returns
        -------
        :class:`str`
            The name of the `section`_ with the 'Resource' prefix removed
        """

        if (name.startswith(cls.Resource)):
            name = name[len(cls.Resource):]

        return name
    
    @classmethod
    def getRemapName(cls, name: str) -> str:
        """
        Changes a `section`_ name to have the keyword 'RemapBlend' to identify that the `section`_
        is created by this fix


        This function either replace the keyword 'Blend' with 'RemapBlend' or adds 'RemapBlend'

        Examples
        --------
        >>> IniFile.getRemapName("EiTriesToUseBlenderAndFails")
        "EiTriesToUseRemapBlenderAndFails"


        >>> IniFile.getRemapName("EiBlendsTheBlender")
        "EiBlendsTheRemapBlender"
    

        >>> IniFile.getRemapName("ResourceCuteLittleEi")
        "ResourceCuteLittleEiRemapBlend"

        Parameters
        ----------
        name: :class:`str`
            The name of the `section`_

        Returns
        -------
        :class:`str`
            The name of the `section`_ with the added 'RemapBlend' keyword
        """

        nameParts = name.rsplit(cls.Blend, 1)
        namePartsLen = len(nameParts)

        if (namePartsLen > 1):
            name = cls.RemapBlend.join(nameParts)
        else:
            name += cls.RemapBlend

        return name

    @classmethod
    def getRemapResourceName(cls, name: str) -> str:
        """
        Changes the name of a section to be a new resource that this fix will create

        .. note::
            See :meth:`IniFile.getResourceName` and :meth:`IniFile.getRemapName` for more info

        Parameters
        ----------
        name: :class:`str`
            The name of the section

        Returns
        -------
        :class:`str`
            The name of the section with the prefix 'Resource' and the keyword 'Remap' added
        """

        name = cls.getRemapName(name)
        if (not name.startswith(cls.Resource)):
            name = cls.getResourceName(name)

        return name

    def _isIfTemplateResource(self, ifTemplatePart: Dict[str, Any]) -> bool:
        """
        Whether the content for some part of a `section`_ contains the key 'vb1'

        Parameters
        ----------
        ifTemplatePart: Dict[:class:`str`, Any]
            The key-value pairs for some part in a `section`_

        Returns
        -------
        :class:`bool`
            Whether 'vb1' is contained in the part
        """

        return self.Vb1 in ifTemplatePart
    
    def _isIfTemplateDraw(self, ifTemplatePart: Dict[str, Any]) -> bool:
        """
        Whether the content for some part of a `section`_ contains the key 'draw'

        Parameters
        ----------
        ifTemplatePart: Dict[:class:`str`, Any]
            The key-value pairs for some part in a `section`_

        Returns
        -------
        :class:`bool`
            Whether 'draw' is contained in the part
        """


        return self.Draw in ifTemplatePart
    
    def _isIfTemplateSubCommand(self, ifTemplatePart: Dict[str, Any]) -> bool:
        """
        Whether the content for some part of a `section`_ contains the key 'run'

        Parameters
        ----------
        ifTemplatePart: Dict[:class:`str`, Any]
            The key-value pairs for some part in a section

        Returns
        -------
        :class:`bool`
            Whether 'run' is contained in the part
        """
                
        return self.Run in ifTemplatePart
    
    def _getIfTemplateResourceName(self, ifTemplatePart: Dict[str, Any]) -> Any:
        """
        Retrieves the value from the key, 'vb1', for some part of a `section`_

        Parameters
        ----------
        ifTemplatePart: Dict[:class:`str`, Any]
            The key-value pairs for some part in a `section`_

        Returns
        -------
        Any
            The corresponding value for the key 'vb1'
        """

        return ifTemplatePart[self.Vb1]
    
    def _getIfTemplateSubCommand(self, ifTemplatePart: Dict[str, Any]) -> Any:
        """
        Retrieves the value from the key, 'run', for some part of a `section`_

        Parameters
        ----------
        ifTemplatePart: Dict[:class:`str`, Any]
            The key-value pairs for some part in a `section`_

        Returns
        -------
        Any
            The corresponding value for the key 'run'
        """

        return ifTemplatePart[self.Run]
    
    # fills the attributes for the sections related to the texture override blend
    def fillTextureOverrideRemapBlend(self, sectionName: str, part: Dict[str, Any], partIndex: int, linePrefix: str, origSectionName: str) -> str:
        """
        Creates the **content part** of an :class:`IfTemplate` for the new sections created by this fix related to the ``[TextureOverride.*Blend.*]`` `sections`_

        .. note::
            For more info about an 'IfTemplate', see :class:`IfTemplate`

        Parameters
        ----------
        sectionName: :class:`str`
            The new name for the section

        part: Dict[:class:`str`, Any]
            The content part of the :class:`IfTemplate` of the original [TextureOverrideBlend] `section`_

        partIndex: :class:`int`
            The index of where the content part appears in the :class:`IfTemplate` of the original `section`_

        linePrefix: :class:`str`
            The text to prefix every line of the created content part

        origSectionName: :class:`str`
            The name of the original `section`_

        Returns
        -------
        :class:`str`
            The created content part
        """

        addFix = ""

        for varName in part:
            varValue = part[varName]

            # filling in the subcommand
            if (varName == self.Run):
                subCommandStr = f"{self.Run} = {self._blendCommandsRemapNames[varValue]}"
                addFix += f"{linePrefix}{subCommandStr}\n"

            # filling in the hash
            if (varName == self.Hash):
                addFix += f"{linePrefix}hash = fe5c0180\n"

            # filling in the vb1 resource
            elif (varName == self.Vb1):
                blendName = self._getIfTemplateResourceName(part)
                remapModel = self.remapBlendModelsDict[blendName]
                fixStr = f'{self.Vb1} = {remapModel.fixedBlendName}'
                addFix += f"{linePrefix}{fixStr}\n"

            # filling in the handling
            elif (varName == self.Handling):
                fixStr = f'{self.Handling} = skip'
                addFix += f"{linePrefix}{fixStr}\n"

            # filling in the draw value
            elif (varName == self.Draw):
                fixStr = f'{self.Draw} = {varValue}'
                addFix += f"{linePrefix}{fixStr}\n"

        return addFix
    
    # fill the attributes for the sections related to the resources
    def fillRemapResource(self, sectionName: str, part: Dict[str, Any], partIndex: int, linePrefix: str, origSectionName: str):
        """
        Creates the **content part** of an :class:`IfTemplate` for the new `sections`_ created by this fix related to the ``[Resource.*Blend.*]`` `sections`_

        .. note::
            For more info about an 'IfTemplate', see :class:`IfTemplate`

        Parameters
        ----------
        sectionName: :class:`str`
            The new name for the `section`_

        part: Dict[:class:`str`, Any]
            The content part of the :class:`IfTemplate` of the original ``[Resource.*Blend.*]`` `section`_

        partIndex: :class:`int`
            The index of where the content part appears in the :class:`IfTemplate` of the original `section`_

        linePrefix: :class:`str`
            The text to prefix every line of the created content part

        origSectionName: :class:`str`
            The name of the original `section`_

        Returns
        -------
        :class:`str`
            The created content part
        """

        addFix = ""

        for varName in part:
            varValue = part[varName]

            # filling in the subcommand
            if (varName == self.Run):
                subCommandStr = f"{self.Run} = {self._resourceCommandsRemapNames[varValue]}"
                addFix += f"{linePrefix}{subCommandStr}\n"

            # add in the type of file
            if (varName == "type"):
                addFix += f"{linePrefix}type = Buffer\n"

            # add in the stride for the file
            if (varName == "stride"):
                addFix += f"{linePrefix}stride = 32\n"

            # add in the file
            if (varName == "filename"):
                remapModel = self.remapBlendModelsDict[origSectionName]
                fixedBlendFile = remapModel.fixedBlendPaths[partIndex]
                addFix += f"{linePrefix}filename = {fixedBlendFile}\n"

        return addFix
    
    # fills the if..else template in the .ini for each section
    def fillIfTemplate(self, sectionName: str, ifTemplate: IfTemplate, fillFunc: Callable[[str, Union[str, Dict[str, Any]], int, int, str], str], origSectionName: Optional[str] = None) -> str:
        """
        Creates a new :class:`IfTemplate` for an existing `section`_ in the .ini file

        Parameters
        ----------
        sectionName: :class:`str`
            The new name of the `section`_

        ifTemplate: :class:`IfTemplate`
            The :class:`IfTemplate` of the orginal `section`_

        fillFunc: Callable[[:class:`str`, Union[:class:`str`, Dict[:class:`str`, Any], :class:`int`, :class:`str`, :class:`str`], :class:`str`]]
            The function to create a new **content part** for the new :class:`IfTemplate`
            :raw-html:`<br />` :raw-html:`<br />`

            .. note::
                For more info about an 'IfTemplate', see :class:`IfTemplate`

            :raw-html:`<br />`
            The parameter order for the function is:

            #. The new section name
            #. The corresponding **content part** in the original :class:`IfTemplate`
            #. The index for the content part in the original :class:`IfTemplate`
            #. The string to prefix every line in the **content part** of the :class:`IfTemplate`
            #. The original name of the section

        origSectionName: Optional[:class:`str`]
            The original name of the section.

            If this argument is set to ``None``, then will assume this argument has the same value as the argument for ``sectionName`` :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ``None``

        Returns
        -------
        :class:`str`
            The text for the newly created :class:`IfTemplate`
        """

        addFix = f"[{sectionName}]\n"
        partIndex = 0
        linePrefix = ""

        if (origSectionName is None):
            origSectionName = sectionName

        for part in ifTemplate:
            # adding in the if..else statements
            if (isinstance(part, str)):
                addFix += part
                
                linePrefix = re.match(r"^[( |\t)]*", part)
                if (linePrefix):
                    linePrefix = linePrefix.group(0)
                    linePrefixLen = len(linePrefix)

                    linePrefix = part[:linePrefixLen]
                    lStrippedPart = part[linePrefixLen:]

                    if (lStrippedPart.find("endif") == -1):
                        linePrefix += "\t"
                partIndex += 1
                continue
            
            # add in the content within the if..else statements
            addFix += fillFunc(sectionName, part, partIndex, linePrefix, origSectionName)

            partIndex += 1
            
        return addFix

    # get the needed lines to fix the .ini file
    @_addFixBoilerPlate
    def getFixStr(self, fix: str = "") -> str:
        """
        Generates the newly added code in the .ini file for the fix

        Parameters
        ----------
        fix: :class:`str`
            Any existing text we want the result of the fix to add onto :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ""

        Returns
        -------
        :class:`str`
            The text for the newly generated code in the .ini file
        """
        hasResources = bool(self.remapBlendModels)
        if (self._blendCommands or hasResources):
            fix += "\n\n"

        # get the fix string for all the texture override blends
        for commandTuple in self._blendCommandsTuples:
            section = commandTuple[0]
            ifTemplate = commandTuple[1]
            commandName = self.getRemapName(section)
            fix += self.fillIfTemplate(commandName, ifTemplate, self.fillTextureOverrideRemapBlend)
            fix += "\n"

        if (hasResources):
            fix += "\n"

        # get the fix string for the resources
        resourceCommandsLen = len(self._resourceCommandsTuples)
        for i in range(resourceCommandsLen):
            commandTuple = self._resourceCommandsTuples[i]
            section = commandTuple[0]
            ifTemplate = commandTuple[1]

            resourceName = self.getRemapName(section)
            fix += self.fillIfTemplate(resourceName, ifTemplate, self.fillRemapResource, origSectionName = section)

            if (i < resourceCommandsLen - 1):
                fix += "\n"

        return fix

    @_readLines
    def injectAddition(self, addition: str, beforeOriginal: bool = True, keepBackup: bool = True, fixOnly: bool = False) -> str:
        """
        Adds and writes new text to the .ini file

        Parameters
        ----------
        addition: :class:`str`
            The text we want to add to the file

        beforeOriginal: :class:`bool`
            Whether to add the new text before the original text :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ``True``

        keepBackup: :class:`bool`
            Whether we want to make a backup copy of the .ini file :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ``True``

        fixOnly: :class:`bool`
            Whether we are only fixing the .ini file without removing any previous changes :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ``False``

        Returns
        -------
        :class:`str`
            The content of the .ini file with the new text added
        """

        original = "".join(self._fileLines)

        if (keepBackup and fixOnly and self.file is not None):
            self.print("log", "Cleaning up and disabling the OLD STINKY ini")
            self.disIni()

        result = ""
        if (beforeOriginal):
            result = f"{addition}\n\n{original}"
        else:
            result = f"{original}\n{addition}"

        # writing the fixed file
        if (self.file is not None):
            with open(self.file, "w", encoding = IniFileEncoding) as f:
                f.write(result)

        self._isRaidenFixed = True
        return result

    @_readLines
    def _removeScriptFix(self) -> str:
        """
        Removes the dedicated section of the code in the .ini file that this script has made  

        Returns
        -------
        :class:`str`
            The new text content of the .ini file
        """

        fileTxt = "".join(self._fileLines)
        fileTxt = re.sub(self._fixRemovalPattern, "", fileTxt)
        fileTxt = fileTxt.strip()
        
        if (self.file is not None):
            with open(self.file, "w", encoding = IniFileEncoding) as f:
                f.write(fileTxt)

            self.clearRead()
        else:
            self._fileLines = fileTxt.split("\n")
            fileLinesLen = len(self._fileLines)

            for i in range(fileLinesLen):
                if (i < fileLinesLen - 1):
                    self._fileLines[i] = f"{self._fileLines[i]}\n"

            self._isRaidenFixed = False

        return fileTxt

    def _removeFix(self) -> str:
        """
        Removes any previous changes that were probably made by this script :raw-html:`<br />` :raw-html:`<br />`

        For the .ini file will remove:

        #. All code surrounded by the *'---...--- Raiden Boss Fix ---...----'* header/footer
        #. All `sections`_ containing the keywords ``RemapBlend``

        Returns
        -------
        :class:`str`
            The new text content of the .ini file with the changes removed
        """

        self._removeScriptFix()        
        if (not self._fileLinesRead):
            self.getFileLines()

        self.removeSectionOptions(self._removalPattern)
        result = self.write()

        if (self.file is not None):
            self.clearRead()
        else:
            self._isRaidenFixed = False

        return result

    @_readLines
    def removeFix(self, keepBackups: bool = True, fixOnly: bool = False) -> str:
        """
        Removes any previous changes that were probably made by this script and creates backup copies of the .ini file

        .. note::
            For more info about what gets removed from the .ini file, see :meth:`IniFile._removeFix`

        Parameters
        ----------
        keepBackup: :class:`bool`
            Whether we want to make a backup copy of the .ini file :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ``True``

        fixOnly: :class:`bool`
            Whether we are only fixing the .ini file without removing any previous changes :raw-html:`<br />` :raw-html:`<br />`

            .. note::
                If this value is set to ``True``, then the previous changes made by this script will not be removed

            **Default**: ``False``

        Returns
        -------
        :class:`str`
            The new text content of the .ini file with the changes removed
        """
        
        if (keepBackups and not fixOnly and self.file is not None):
            self.print("log", f"Creating Backup for {os.path.basename(self.file)}")
            self.disIni()

        if (fixOnly):
            return "".join(self._fileLines)

        if (self.file is not None):
            self.print("log", f"Removing any previous changes from this script in {os.path.basename(self.file)}")

        result = self._removeFix()
        return result


    def _makeRemapModels(self) -> Dict[str, RemapBlendModel]:
        """
        Low level function to create all the data needed for fixing the ``[Resource.*Blend.*]`` `sections`_ in the .ini file

        Returns
        -------
        Dict[:class:`str`, :class:`RemapBlendModel`]
            The data for fixing the resource `sections`_

            The keys are the names for the resource `sections`_ and the values are the required data for fixing the `sections`_
        """

        folderPath = CurrentDir
        if (self.file is not None):
            folderPath = os.path.dirname(self.file)
        
        for resourceKey in self._resourceCommands:
            resourceIftemplate = self._sectionIfTemplates[resourceKey]
            fixedBlendName = self.getRemapResourceName(resourceKey)
            origBlendPaths = {}
            fixedBlendPaths = {}

            partIndex = 0
            for part in resourceIftemplate:
                if (isinstance(part,str)):
                    partIndex += 1
                    continue

                origBlendFile = None
                try:
                    origBlendFile = FileService.parseOSPath(part['filename'])
                except KeyError:
                    partIndex += 1
                    continue

                fixedBlendPath = self.getFixedBlendFile(origBlendFile)
                origBlendPaths[partIndex] = origBlendFile
                fixedBlendPaths[partIndex] = fixedBlendPath

                partIndex += 1

            remapBlendModel = RemapBlendModel(folderPath, fixedBlendName, fixedBlendPaths, origBlendName = resourceKey, origBlendPaths = origBlendPaths)
            self.remapBlendModelsDict[resourceKey] = remapBlendModel

        self.remapBlendModels = list(self.remapBlendModelsDict.values())
        return self.remapBlendModelsDict

    def _getSubCommands(self, ifTemplate: IfTemplate, currentSubCommands: Set[str], subCommands: Set[str], subCommandLst: List[str]):
        for partIndex in ifTemplate.calledSubCommands:
            subCommand = ifTemplate.calledSubCommands[partIndex]
            if (subCommand not in subCommands):
                currentSubCommands.add(subCommand)
                subCommands.add(subCommand)
                subCommandLst.append(subCommand)

    def _getCommandIfTemplate(self, sectionName: str, raiseException: bool = True) -> Optional[IfTemplate]:
        """
        Low level function for retrieving the :class:`IfTemplate` for a certain `section`_ from `IniFile._sectionIfTemplate`

        Parameters
        ----------
        sectionName: :class:`str`
            The name of the `section`_

        raiseException: :class:`bool`
            Whether to raise an exception when the section's :class:`IfTemplate` is not found

        Raises
        ------
        :class:`KeyError`
            If the :class:`IfTemplate` for the `section`_ is not found and ``raiseException`` is set to `True`

        Returns
        -------
        Optional[:class:`IfTemplate`]
            The corresponding :class:`IfTemplate` for the `section`_
        """
        try:
            ifTemplate = self._sectionIfTemplates[sectionName]
        except BaseException as e:
            if (raiseException):
                raise KeyError(f"The section by the name '{sectionName}' does not exist") from e
            else:
                return None
        else:
            return ifTemplate

    def _getBlendResources(self, sectionName: str, blendResources: Set[str], subCommands: Set[str], subCommandLst: List[str]):
        """
        Low level function for retrieving all the referenced resources that were called by `sections`_ related to the ``[TextureOverride.*Blend.*]`` `sections`_

        Parameters
        ----------
        sectionName: :class:`str`
            The name of the `section`_ in the .ini file that we want to get the blend resources from

        blendResources: Set[:class:`str`]
            The result for all the resource `sections`_ that were referenced

        subCommands: Set[:class:`str`]
            The result for all of the sub-sections that were called from the ``[TextureOverride.*Blend.*]`` `section`_

        subCommandLst: List[:class:`str`]
            The result for all of the sub-sections that were called from the ``[TextureOverride.*Blend.*]`` `section`_ that maintains the order
            the `sections`_ are called in the call stack

        Raises
        ------
        :class:`KeyError`
            If the :class:`IfTemplate` is not found for some `section`_ related to the ``[TextureOverride.*Blend.*]`` `section`_
        """

        ifTemplate = self._getCommandIfTemplate(sectionName)
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
        self._getSubCommands(ifTemplate, currentSubCommands, subCommands, subCommandLst)

        # get the blend resources from other subcommands
        for sectionName in currentSubCommands:
            self._getBlendResources(sectionName, blendResources, subCommands, subCommandLst)

    def _getCommands(self, sectionName: str, subCommands: Set[str], subCommandLst: List[str]):
        """
        Low level function for retrieving all the commands/`sections`_ that are called from a certain `section`_ in the .ini file

        Parameters
        ----------
        sectionName: :class:`str`
            The name of the `section`_ we are starting from

        subCommands: Set[:class:`str`]
            The result for all of the `sections`_ that were called

        subCommandLst: List[:class:`str`]
            The result for all of the `sections`_ that were called while maintaining the order
            the `sections`_ are called in the call stack

        Raises
        ------
        :class:`KeyError`
            If the :class:`IfTemplate` is not found for some `section`_
        """

        currentSubCommands = set()
        ifTemplate = self._getCommandIfTemplate(sectionName)

        # add in the current command if it has not been added yet
        if (sectionName not in subCommands):
            subCommands.add(sectionName)
            subCommandLst.append(sectionName)

        # get all the unvisited subcommand sections to visit
        self._getSubCommands(ifTemplate, currentSubCommands, subCommands, subCommandLst)

        # visit the children subcommands that have not been visited yet
        for sectionName in currentSubCommands:
            self._getCommands(sectionName, subCommands, subCommandLst)

    # parse(): Parses the merged.ini file for any info needing to keep track of
    def parse(self):
        """
        Parses the .ini file

        Raises
        ------
        :class:`KeyError`
            If a certain resource `section`_ is not found :raw-html:`<br />` :raw-html:`<br />`
            
            (either the name of the `section`_ is not found in the .ini file or the `section`_ was skipped due to some error when parsing the `section`_)
        """

        self._sectionIfTemplates = self.getSectionOptions(self._sectionPattern, postProcessor = self._processIfTemplate)

        try:
            self._sectionIfTemplates[self._textureOverrideBlendRoot]
        except:
            return

        self._isRaidenIni = True
        blendResources = set()
        subCommands = { self._textureOverrideBlendRoot }
        subCommandLst = [self._textureOverrideBlendRoot]
        resourceCommands = set()
        resourceCommandLst = []

        # keep track of all the needed blend dependencies
        self._getBlendResources(self._textureOverrideBlendRoot, blendResources, subCommands, subCommandLst)

        # read in all the needed dependencies
        for blend in blendResources:
            try:
                self._resourceBlends[blend] = self._sectionIfTemplates[blend]
            except BaseException as e:
                raise KeyError(f"The resource by the name, '{blend}', does not exist") from e
            else:
                resourceCommands.add(blend)
                resourceCommandLst.append(blend)

        # sort the resources
        resourceCommandLst.sort(key = lambda resourceName: self._getResourceSortKey((resourceName, None)))

        # keep track of all the subcommands that the resources call
        for blend in blendResources:
            self._getCommands(blend, resourceCommands, resourceCommandLst)

        self._blendCommands = {}
        self._blendCommandsRemapNames = {}
        for subCommand in subCommands:
            self._blendCommands[subCommand] = self._sectionIfTemplates[subCommand]
            self._blendCommandsRemapNames[subCommand] = self.getRemapName(subCommand)

        self._resourceCommands = {}
        self._resourceCommandsRemapNames = {}
        for subCommand in resourceCommands:
            self._resourceCommands[subCommand] = self._sectionIfTemplates[subCommand]
            self._resourceCommandsRemapNames[subCommand] = self.getRemapName(subCommand)

        self._blendCommandsTuples = list(map(lambda subCommand: (subCommand, self._blendCommands[subCommand]), subCommandLst))
        self._resourceCommandsTuples = list(map(lambda subCommand: (subCommand, self._resourceCommands[subCommand]), resourceCommandLst))   

        self._makeRemapModels()


    def fix(self, keepBackup: bool = True, fixOnly: bool = False) -> str:
        """
        Fixes the .ini file

        Parameters
        ----------
        keepBackup: :class:`bool`
            Whether we want to make a backup copy of the .ini file :raw-html:`<br />` :raw-html:`<br />`

            **Default**: `True`

        fixOnly: :class:`bool`
            Whether we are only fixing the .ini file without removing any previous changes :raw-html:`<br />` :raw-html:`<br />`

            **Default**: `False`

        Returns
        -------
        :class:`str`
            The new content of the .ini file which includes the fix
        """

        fix = ""
        fix += self.getFixStr(fix = fix)
        return self.injectAddition(f"\n\n{fix}", beforeOriginal = False, keepBackup = keepBackup, fixOnly = fixOnly)


class Mod(Model):
    """
    This Class inherits from :class:`Model`

    Used for handling a mod

    .. note::
        We define **a mod** based off the following criteria:

        * A folder that contains at least 1 .ini file
        * At least 1 of the .ini files in the folder contains:

            * a section with the regex ``[.*TextureOverride.*(Raiden|Shogun).*]`` if :attr:`RaidenBossFixService.readAllInis` is set to ``False`` :raw-html:`<br />` **OR** :raw-html:`<br />`
            * a section with the regex ``[.*TextureOverride.*Blend.*]`` if :attr:`RaidenBossFixService.readAllInis` is set to ``True`` or the script is ran with the ``--all`` flag


    Parameters
    ----------
    path: Optional[:class:`str`]
        The file location to the mod folder. :raw-html:`<br />` :raw-html:`<br />`
        
        If this value is set to ``None``, then will use the current directory of where this module is loaded.
        :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``None``

    files: Optional[List[:class:`str`]]
        The direct children files to the mod folder (does not include files located in a folder within the mod folder). :raw-html:`<br />` :raw-html:`<br />`

        If this parameter is set to ``None``, then the class will search the files for you when the class initializes :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``None``

    logger: Optional[:class:`Logger`]
        The logger used to pretty print messages :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``None``

    Attributes
    ----------
    path: Optional[:class:`str`]
        The file location to the mod folder

    _files: List[:class:`str`]
        The direct children files to the mod folder (does not include files located in a folder within the mod folder).

    logger: Optional[:class:`Logger`]
        The logger used to pretty print messages

    inis: List[:class:`str`]
        The .ini files found for the mod

    remapBlend: List[:class:`str`]
        The RemapBlend.buf files found for the mod

    backupInis: List[:class:`str`]
        The DISABLED_RSFixBackup.txt files found for the mod

    backupDups: List[:class:`str`]
        The DISABLED_RSDup.txt files found for the mod

        .. warning::
            This attribute is now DEPRECATED. Now, the fix does not care whether there are duplicate .ini files or Blend.buf files
    """
    def __init__(self, path: Optional[str] = None, files: Optional[List[str]] = None, logger: Optional[Logger] = None):
        super().__init__(logger = logger)
        self.path = FileService.getPath(path)
        self._files = files
        self._setupFiles()

        self.inis, self.remapBlend, self.backupInis, self.backupDups = self.getOptionalFiles()
        self.inis = list(map(lambda iniPath: IniFile(iniPath, logger = logger), self.inis))

    @property
    def files(self):
        """
        The direct children files to the mod folder (does not include files located in a folder within the mod folder).

        :getter: Returns the files to the mod
        :setter: Sets up the files for the mod
        :type: Optional[List[:class:`str`]]
        """

        return self._files

    @files.setter
    def files(self, newFiles: Optional[List[str]] = None):
        self._files = newFiles
        self._setupFiles()

    def _setupFiles(self):
        """
        Searches the direct children files to the mod folder if :attr:`Mod.files` is set to ``None``        
        """

        if (self._files is None):
            self._files = FileService.getFiles(path = self.path)

    @classmethod
    def isIni(cls, file: str) -> bool:
        """
        Determines whether the file is a .ini file which is the file used to control how a mod behaves

        Parameters
        ----------
        file: :class:`str`
            The file path to check

        Returns
        -------
        :class:`bool`
            Whether the passed in file is a .ini file
        """

        return file.endswith(IniExt)
    
    @classmethod
    def isRemapBlend(cls, file: str) -> bool:
        """
        Determines whether the file is a RemapBlend.buf file which is the fixed Blend.buf file created by this fix

        Parameters
        ----------
        file: :class:`str`
            The file path to check

        Returns
        -------
        :class:`bool`
            Whether the passed in file is a RemapBlend.buf file
        """

        baseName = os.path.basename(file)
        if (not baseName.endswith(BufExt)):
            return False

        baseName = baseName.rsplit(".", 1)[0]
        baseNameParts = baseName.rsplit("RemapBlend", 1)

        return (len(baseNameParts) > 1)
    
    @classmethod
    def isBlend(cls, file: str) -> bool:
        """
        Determines whether the file is a Blend.buf file which is the original blend file provided in the mod

        Parameters
        ----------
        file: :class:`str`
            The file path to check

        Returns
        -------
        :class:`bool`
            Whether the passed in file is a Blend.buf file
        """

        return bool(file.endswith(BlendFileType) and not cls.isRemapBlend(file))
   
    @classmethod
    def isBackupIni(cls, file: str) -> bool:
        """
        Determines whether the file is a DISABLED_RSFixBackup.txt file that is used to make
        backup copies of .ini files

        Parameters
        ----------
        file: :class:`str`
            The file path to check

        Returns
        -------
        :class:`bool`
            Whether the passed in file is a DISABLED_RSFixBackup.txt file
        """
        
        return BackupFilePrefix in file and file.endswith(TxtExt)
    
    @classmethod
    def isBackupDupFile(cls, file: str) -> bool:
        """
        .. warning::
            This function is now DEPRECATED. Now, the fix does not care whether there are duplicate .ini files or Blend.buf files

        Determines whether the file is a DISABLED_RSDup.txt file that is used to disable duplicate .ini files
        or Blend.buf files

        Parameters
        ----------
        file: :class:`str`
            The file path to check

        Returns
        -------
        :class:`bool`
            Whether the passed in file is a DISABLED_RSDup.txt file
        """
                
        return DuplicateFilePrefix in file and file.endswith(TxtExt)

    def getOptionalFiles(self) -> List[Optional[str]]:
        """
        Retrieves a list of each type of files that are not mandatory for the mod

        Returns
        -------
        [ List[:class:`str`], List[:class:`str`], List[:class:`str`], List[:class:`str`] ]
            The resultant files found for the following file categories (listed in the same order as the return type):

            #. .ini files
            #. .RemapBlend.buf files
            #. DISABLED_RSFixBackup.txt files
            #. DISABLED_RSDup.txt files

            .. note::
                See :meth:`Mod.isIni`, :meth:`Mod.isRemapBlend`, :meth:`Mod.isBackupIni` or :meth:`Mod.isBackupDupFile` for the specifics of each type of file
        """

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
        """
        Removes all DISABLED_RSFixBackup.txt contained in the mod
        """

        for file in self.backupInis:
            self.print("log", f"Removing the backup ini, {os.path.basename(file)}")
            os.remove(file)

    def removeBackupDups(self):
        """
        Removes all DISABLED_RSDup.txt contained in the mod
        """

        for file in self.backupDups:
            self.print("log", f"Removing the unused duplicate file, {os.path.basename(file)}")
            os.remove(file)

    def removeFix(self, fixedBlends: Set[str], fixedInis: Set[str], keepBackups: bool = True, fixOnly: bool = False):
        """
        Removes any previous changes done by this module's fix

        Parameters
        ----------
        fixedBlend: Set[:class:`str`]
            The file paths to the RemapBlend.buf files that we do not want to remove

        fixedInis: Set[:class:`str`]
            The file paths to the .ini files that we do not want to remove

        keepBackups: :class:`bool`
            Whether to create or keep DISABLED_RSFixBackup.txt files in the mod :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ``True``

        fixOnly: :class:`bool`
            Whether to not undo any changes created in the .ini files :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ``False``
        """

        filesRemoved = False
        if (self.remapBlend is not None):
            for remapBlend in self.remapBlend:
                remapBlendFullPath = FileService.absPathOfRelPath(remapBlend, self.path)

                # remove only remap blends that have not been recently created
                if (remapBlendFullPath not in fixedBlends):
                    self.print("log", f"Removing previous {RemapBlendFile} at {os.path.basename(remapBlend)}")
                    os.remove(remapBlend)

                    if (not filesRemoved):
                        filesRemoved = True

        for ini in self.inis:
            iniFullPath = FileService.absPathOfRelPath(ini.file, self.path)
            if (iniFullPath not in fixedInis and ini.isRaidenIni):
                ini.removeFix(keepBackups = keepBackups, fixOnly = fixOnly)

                if (not filesRemoved):
                    filesRemoved = True

        if (filesRemoved):
            self.print("space")

    # correcting the blend file
    @classmethod
    def blendCorrection(self, blendFile: Union[str, bytes], fixedBlendFile: Optional[str] = None) -> Union[str, bytes]:
        """
        Fixes a Blend.buf file

        Parameters
        ----------
        blendFile: Union[:class:`str`, :class:`bytes`]
            The file path to the Blend.buf file to fix

        fixedBlendFile: Optional[:class:`str`]
            The file path for the fixed Blend.buf file :raw-html:`<br />` :raw-html:`<br />`

            **Default**: ``None``

        Raises
        ------
        :class:`BlendFileNotRecognized`
            If the original Blend.buf file provided by the parameter ``blendFile`` cannot be read

        Returns
        -------
        Union[:class:`str`, :class:`bytes`]
            If the argument ``fixedBlendFile`` is ``None``, then will return bytes for the fixed Blend.buf file :raw-html:`<br />` :raw-html:`<br />`
            Otherwise will return the filename fo the fixed RemapBlend.buf file
        """

        blendData = None
        if (isinstance(blendFile, str)):
            with open(blendFile, "rb") as f:
                blendData = f.read()
        else:
            blendData = blendFile

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

        if (fixedBlendFile is not None):
            with open(fixedBlendFile, "wb") as f:
                f.write(result)

            return fixedBlendFile

        return result
    
    def correctBlend(self, fixedRemapBlends: Dict[str, RemapBlendModel]):
        """
        Fixes all the Blend.buf files reference by the mod

        Requires all the .ini files in the mod to have ran their :meth:`IniFile.parse` function

        Parameters
        ----------
        fixedRemapBlends: Dict[:class:`str`, :class:`RemapBlendModel`]
            All of the RemapBlend.buf files that have already been fixed.
            :raw-html:`<br />`
            :raw-html:`<br />`
            The keys are the absolute filepath to the fixed RemapBlend.buf file and the values contains the data related
            to the fixed RemapBlend.buf file
        """

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
    """
    The overall class for fixing the Raiden Shogun Boss for Raiden Shogun mods

    Parameters
    ----------
    path: Optional[:class:`str`]
        The file location of where to run the fix. :raw-html:`<br />` :raw-html:`<br />`

        If this attribute is set to ``None``, then will run the fix from wherever this class is called :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``None``

    keepBackups: :class:`bool`
        Whether to keep backup versions of any .ini files that the script fixes :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``True``

    fixOnly: :class:`bool`
        Whether to only fix the mods without removing any previous changes this fix script may have made :raw-html:`<br />` :raw-html:`<br />`

        .. warning::
            if this is set to ``True`` and :attr:`undoOnly` is also set to ``True``, then the fix will not run and will throw a :class:`ConflictingOptions` exception

        :raw-html:`<br />`

        **Default**: ``False``

    undoOnly: :class:`bool`
        Whether to only undo the fixes previously made by the fix :raw-html:`<br />` :raw-html:`<br />`

        .. warning::
            if this is set to ``True`` and :attr:`fixOnly` is also set to ``True``, then the fix will not run and will throw a :class:`ConflictingOptions` exception

        :raw-html:`<br />`

        **Default**: ``True``

    readAllInis: :class:`bool`
        Whether to read all the .ini files that the fix encounters :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``False``

    log: :class:`bool`
        Whether to log the run of the fix in a seperate text file :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``False``

    verbose: :class:`bool`
        Whether to print the progress for fixing mods :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``True``

    handleExceptions: :class:`bool`
        When an exception is caught, whether to silently stop running the fix :raw-html:`<br />` :raw-html:`<br />`

        **Default**: ``False``

    Attributes
    ----------
    log: :class:`bool`
        Whether to log the run of the fix in a seperate text file

    _loggerBasePrefix: :class:`str`
        The prefix string for the logger used when the fix returns back to the original directory that it started to run

    logger: :class:`Logger`
        The logger used to pretty print messages

    _path: :class:`str`
        The file location of where to run the fix.

    keepBackups: :class:`bool`
        Whether to keep backup versions of any .ini files that the script fixes

    fixOnly: :class:`bool`
        Whether to only fix the mods without removing any previous changes this fix script may have made

    undoOnly: :class:`bool`
        Whether to only undo the fixes previously made by the fix

    readAllInis: :class:`bool`
        Whether to read all the .ini files that the fix encounters

    verbose: :class:`bool`
        Whether to print the progress for fixing mods

    handleExceptions: :class:`bool`
        When an exception is caught, whether to silently stop running the fix

    _logFile: :class:`str`
        The file path of where to generate a log .txt file

    _pathIsCWD: :class:`bool`
        Whether the filepath that the program runs from is the current directory where this module is loaded

    modsFixed: :class:`int`
        The number of mods that have been fixed

    skippedMods: Dict[:class:`str`, :class:`BaseException`]
        All the mods that have been skipped :raw-html:`<br />` :raw-html:`<br />`

        The keys are the absolute path to the mod folder and the values are the exception that caused the mod to be skipped

    blendsFound: :class:`int`
        The number of Blend.buf files found within the found mods

    blendsFixed: Set[:class:`str`]
        The absolute paths to all the Blend.buf files that have been fixed

    skippedBlends: Dict[:class:`str`, Dict[:class:`str`, :class:`BaseException`]]
        The Blend.buf files that got skipped :raw-html:`<br />` :raw-html:`<br />`

        * The outer key is the absolute path to the mod folder
        * The inner key is the absolute path to the Blend.buf file
        * The value in the inner dictionary is the exception that caused the Blend.buf file to be skipped

    skippedBlendsCount: :class:`int`
        The count for how many Blend.buf files got skipped

    inisFixed: Set[:class:`str`]
        The absolute paths to the fixed .ini files

    inisSkipped: Dict[:class:`str`, :class:`BaseException`]
        The .ini files that got skipped :raw-html:`<br />` :raw-html:`<br />`

        The keys are the absolute file paths to the .ini files and the values are exceptions that caused the .ini file to be skipped
    """

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
        self.modsFixed = 0
        self.skippedMods: Dict[str, BaseException] = {}
        self.blendsFound = 0
        self.blendsFixed: Set[str] = set()
        self.skippedBlends: Dict[str, Dict[str, BaseException]] = {}
        self.skippedBlendsCount = 0
        self.inisFixed = set()
        self.inisSkipped: Dict[str, BaseException] = {}

        self._setupModPath()

    @property
    def pathIsCwd(self):
        """
        Whether the filepath that the program runs from is the current directory where this module is loaded

        :getter: Returns whether the filepath that the program runs from is the current directory of where the module is loaded
        :type: :class:`bool`
        """

        return self._pathIsCwd
    
    @property
    def path(self) -> str:
        """
        The filepath of where the fix is running from

        :getter: Returns the path of where the fix is running
        :setter: Sets the path for where the fix runs
        :type: :class:`str`
        """

        return self._path
    
    @path.setter
    def path(self, newPath: str):
        self._path = newPath
        self._setupModPath()
        self.skippedMods = {}
    
    def _setupModPath(self):
        """
        Sets the filepath of where the fix will run from
        """

        self._pathIsCwd = False
        if (self._path is None):
            self._path = DefaultPath
            self._pathIsCwd = True
            return

        self._path = FileService.parseOSPath(self._path)
        self._path = os.path.abspath(self._path)
        self._pathIsCwd = (self._path == DefaultPath)
    
    # fixes an ini file in a mod
    def fixIni(self, ini: IniFile, mod: Mod, fixedRemapBlends: Dict[str, RemapBlendModel]) -> bool:
        """
        Fixes an individual .ini file for a particular mod

        .. note:: 
            For more info about how we define a 'mod', go to :class:`Mod`

        Parameters
        ----------
        ini: :class:`IniFile`
            The .ini file to fix

        mod: :class:`Mod`
            The mod being fixed

        fixedRemapBlends: Dict[:class:`str`, :class:`RemapBlendModel`]
            All of the RemapBlend.buf files that have already been fixed.
            :raw-html:`<br />`
            :raw-html:`<br />`
            The keys are the absolute filepath to the fixed RemapBlend.buf file and the values contains the data related
            to the fixed RemapBlend.buf file

        Returns
        -------
        :class:`bool`
            Whether the particular .ini file has been fixed
        """

        # check if the .ini is for a raiden mod
        if (ini is None or not ini.isRaidenIni):
            return False

        # parse the .ini file even if we are only undoing fixes for the case where a Blend.buf file
        #   forms a bridge with some disconnected folder subtree of a mod
        if (self.undoOnly):
            ini.parse()
            return True

        fileBaseName = os.path.basename(ini.file)

        # parse the .ini file
        self.logger.log(f"Parsing {fileBaseName}...")
        ini.parse()
        if (ini.isRaidenFixed):
            self.logger.log(f"the ini file, {fileBaseName}, is already fixed")
            return False

        # fix the blends
        self.logger.log(f"Fixing the {BlendFileType} files for {fileBaseName}...")
        currentBlendsFound, currentBlendsFixed, currentBlendsSkipped = mod.correctBlend(fixedRemapBlends = fixedRemapBlends)
        self.blendsFound += currentBlendsFound
        self.blendsFixed = self.blendsFixed.union(currentBlendsFixed)

        if (currentBlendsSkipped):
            self.skippedBlends[mod.path] = currentBlendsSkipped
        self.skippedBlendsCount += len(currentBlendsSkipped)

        # writing the fixed file
        self.logger.log(f"Making the fixed ini file for {fileBaseName}")
        ini.fix(keepBackup = self.keepBackups, fixOnly = self.fixOnly)

        return True

    # fixes a mod
    def fixMod(self, mod: Mod, fixedRemapBlends: Dict[str, RemapBlendModel]) -> bool:
        """
        Fixes a particular mod

        .. note:: 
            For more info about how we define a 'mod', go to :class:`Mod`

        Parameters
        ----------
        mod: :class:`Mod`
            The mod being fixed

        fixedRemapBlends: Dict[:class:`str`, :class:`RemapBlendModel`]
            all of the RemapBlend.buf files that have already been fixed.
            :raw-html:`<br />` :raw-html:`<br />`
            The keys are the absolute filepath to the fixed RemapBlend.buf files and the values contains the data related
            to the fixed RemapBlend.buf file

        Returns
        -------
        :class:`bool`
            Whether the particular mod has been fixed
        """

        # remove any backups
        if (not self.keepBackups):
            mod.removeBackupInis()

        for ini in mod.inis:
            ini.checkRaidenIni(mustBeRaiden = not self.readAllInis)

        # undo any previous fixes
        if (not self.fixOnly):
            mod.removeFix(self.blendsFixed, self.inisFixed, keepBackups = self.keepBackups)

        result = False
        firstIniException = None
        inisLen = len(mod.inis)

        for i in range(inisLen):
            ini = mod.inis[i]
            iniIsFixed = False

            try:
                iniIsFixed = self.fixIni(ini, mod, fixedRemapBlends)
            except BaseException as e:
                self.logger.handleException(e)
                self.inisSkipped[ini.file] = e 

                if (firstIniException is None):
                    firstIniException = e

            result = (result or iniIsFixed)

            if (not iniIsFixed):
                continue
            
            if (i < inisLen - 1):
                self.logger.space()
            iniFullPath = FileService.absPathOfRelPath(ini.file, mod.path)
            self.inisFixed.add(iniFullPath)
        
        if (firstIniException is not None):
            self.skippedMods[mod.path] = firstIniException

        return result
    
    def addTips(self):
        """
        Prints out any useful tips for the user to know
        """

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
        """
        Prints out the exception message for why a particular .ini file or Blend.buf file has been skipped

        Parameters
        ----------
        assetName: :class:`str`
            The name for the type of asset (files, folders, mods, etc...) that was skipped

        assetDict: Dict[:class:`str`, :class:`BaseException`]
            Locations of where exceptions have occured for the particular asset :raw-html:`<br />` :raw-html:`<br />`

            The keys are the absolute folder paths to where the exception occured

        wantStrFunc: Callable[[:class:`str`], :class:`str`]
            Function for how we want to print out the warning for each exception :raw-html:`<br />` :raw-html:`<br />`

            Takes in the folder location of where the exception occured as a parameter
        """

        if (assetDict):
            message = f"WARNING: The following {assetName} were skipped due to warnings (see log above):\n\n"
            for dir in assetDict:
                message += warnStrFunc(dir)

            self.logger.error(message)
            self.logger.space()

    def warnSkippedBlends(self, modPath: str):
        """
        Prints out all of the Blend.buf files that were skipped due to exceptions

        Parameters
        ----------
        modPath: :class:`str`
            The absolute path to a particular folder
        """

        relModPath = FileService.getRelPath(modPath, self._path)
        message = f"Mod: {relModPath}\n"
        blendWarnings = self.skippedBlends[modPath]
        
        for blendPath in blendWarnings:
            relBlendPath = FileService.getRelPath(blendPath, self._path)
            message += self.logger.getBulletStr(f"{relBlendPath} >>> {blendWarnings[blendPath]}\n")
        
        message += "\n"
        return message

    def reportSkippedMods(self):
        """
        Prints out all of the mods that were skipped due to exceptions

        .. note:: 
            For more info about how we define a 'mod', go to :class:`Mod`
        """

        self.reportSkippedAsset("mods", self.skippedMods, lambda dir: self.logger.getBulletStr(f"{dir} >>> {self.skippedMods[dir]}\n"))
        self.reportSkippedAsset(f"{IniFileType}s", self.inisSkipped, lambda file: self.logger.getBulletStr(f"{file} >>> {self.inisSkipped[file]}\n"))
        self.reportSkippedAsset(f"{BlendFileType} files", self.skippedBlends, lambda dir: self.warnSkippedBlends(dir))

    def reportSummary(self):
        skippedMods = len(self.skippedMods)
        foundMods = self.modsFixed + skippedMods
        fixedBlends = len(self.blendsFixed)
        skippedBlends = self.blendsFound - fixedBlends
        fixedInis = len(self.inisFixed)
        skippedInis = len(self.inisSkipped)
        foundInis = fixedInis + skippedInis

        self.logger.openHeading("Summary", sideLen = 10)
        self.logger.space()
        
        modFixMsg = ""
        blendFixMsg = ""
        iniFixMsg = ""
        if (not self.undoOnly):
            modFixMsg = f"Out of {foundMods} found mods, fixed {self.modsFixed} mods and skipped {skippedMods} mods"
            iniFixMsg = f"Out of the {foundInis} {IniFileType}s within the found mods, fixed {fixedInis} {IniFileType}s and skipped {skippedInis} {IniFileType} files"
            blendFixMsg = f"Out of the {self.blendsFound} {BlendFileType} files within the found mods, fixed {fixedBlends} {BlendFileType} files and skipped {skippedBlends} {BlendFileType} files"
        else:
            modFixMsg = f"Out of {foundMods} found mods, remove fix from {self.modsFixed} mods and skipped {skippedMods} mods"

        self.logger.bulletPoint(modFixMsg)
        if (iniFixMsg):
            self.logger.bulletPoint(iniFixMsg)

        if (blendFixMsg):
            self.logger.bulletPoint(blendFixMsg)

        self.logger.space()
        self.logger.closeHeading()

    def createLog(self):
        """
        Creates a log text file that contains all the text printed on the command line
        """

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

    def createMod(self, path: Optional[str] = None, files: Optional[List[str]] = None) -> Mod:
        """
        Creates a mod

        .. note:: 
            For more info about how we define a 'mod', go to :class:`Mod`

        Parameters
        ----------
        path: Optional[:class:`str`]
            The absolute path to the mod folder. :raw-html:`<br />` :raw-html:`<br />`
            
            If this argument is set to ``None``, then will use the current directory of where this module is loaded

        files: Optional[List[:class:`str`]]
            The direct children files to the mod folder (does not include files located in a folder within the mod folder). :raw-html:`<br />` :raw-html:`<br />`

            If this parameter is set to ``None``, then the module will search the folders for you

        Returns
        -------
        :class:`Mod`
            The mod that has been created
        """

        path = FileService.getPath(path)
        mod = Mod(path = path, files = files, logger = self.logger)
        return mod

    def _fix(self):
        """
        The overall logic for fixing a bunch of mods

        For finding out which folders may contain mods, this function:
            #. recursively searches all folders from where the :attr:`RaidenBossFixService.path` is located
            #. for every .ini file in a valid mod and every Blend.buf file encountered that is encountered, recursively search all the folders from where the .ini file or Blend.buf file is located

        .. note:: 
            For more info about how we define a 'mod', go to :class:`Mod`
        """

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
                    self.skippedMods[path] = e

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
                self.modsFixed += 1

            visitingDirs.remove(path)
            visitedDirs.add(path)

        self.logger.split()
        self.logger.prefix = self._loggerBasePrefix
        self.reportSkippedMods()
        self.logger.space()
        self.reportSummary()


    def fix(self):
        """
        Fixes a bunch of mods

        see :meth:`_fix` for more info
        """
        
        try:
            self._fix()
        except BaseException as e:
            if (self.handleExceptions):
                self.logger.handleException(e)
            else:
                self.createLog()
                raise e from e
        else:
            noErrors = bool(not self.skippedMods and not self.skippedBlends)

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