import copy
import csv
import hashlib
import json
import os
import shutil
import xml.etree.ElementTree as ET

import click 

@click.group
def mycommands():
    pass

class BnkXmlObject:
    """
    Class to extract unhashed wem names from the xmls that accompany every bnk in Jedi Survivor. 
    This class is only designed to read the xmls as from my tests there doesn't appear to be any need to modify the contents, though some specific situations may require the precache size or length to be modified.
    There are also json files which (hopefully) contains the same information as the xmls, thus making parsing them redundant unless they need to be modified in the reimport stage.
    """
    def __init__(self, s_file_name):
        self.FileData = {}
        _tree = ET.parse(s_file_name)
        if (_tree.getroot().find("SoundBanks") is None):
                return
        for e_sound_bank in _tree.getroot().find("SoundBanks").findall("SoundBank"):
            if (e_sound_bank.find("IncludedEvents") is None):
                if (e_sound_bank.find("ReferencedStreamedFiles") is not None or e_sound_bank.find("ReferencedStreamedFiles") is not None):
                     raise Exception("Logic error")
                continue
            for e_included_events in e_sound_bank.find("IncludedEvents").findall("Event"):
                event_name = e_included_events.attrib["Name"]
                self.read_file_data(e_included_events, "ReferencedStreamedFiles", event_name)
                self.read_file_data(e_included_events, "IncludedMemoryFiles", event_name)
            self.read_file_data(e_sound_bank, "ReferencedStreamedFiles", event_name)
            self.read_file_data(e_sound_bank, "IncludedMemoryFiles", event_name)

    def read_file_data(cls, e_fileevents, events_name, cak_name = None):
        if (e_fileevents.find(events_name) is not None):
            for e_file in e_fileevents.find(events_name).findall("File"):
                o_xml_wem = WemXmlObject(e_file, cak_name)

                if o_xml_wem.ShortName not in cls.FileData:
                    cls.FileData[o_xml_wem.ShortName] = o_xml_wem
                else:
                    if len(o_xml_wem.Events) > 0 and o_xml_wem.Events[0] not in cls.FileData[o_xml_wem.ShortName].Events:
                        cls.FileData[o_xml_wem.ShortName].Events.append(o_xml_wem.Events[0])
                    if list(o_xml_wem.Files.keys())[0] not in  cls.FileData[o_xml_wem.ShortName].Files:
                        cls.FileData[o_xml_wem.ShortName].Files[list(o_xml_wem.Files.keys())[0]] = list(o_xml_wem.Files.values())[0]

    def create_hash_pairs(cls, wem_directory, hash_to_unhash = True):
        d_pairs = {}
        for short_name in cls.FileData:
            add_suffix = False
            if len(cls.FileData[short_name].Files) > 1:
                current_hash = None
                for hash_name in cls.FileData[short_name].Files:
                    hash_file = os.path.join(wem_directory, hash_name + ".wem")
                    if os.path.exists(hash_file):
                        new_hash = md5(hash_file)
                        if new_hash != current_hash:
                            if current_hash == None:
                                current_hash = new_hash
                            else:
                                add_suffix = True
                                break
                    else:
                        add_suffix = True
                        break

            for hash_name in cls.FileData[short_name].Files:
                unhashed_name = short_name
                if add_suffix:
                    unhashed_name = short_name + "_" + cls.FileData[short_name].Files[hash_name].split("_")[-1]

                if hash_to_unhash:
                    d_pairs[hash_name] = [unhashed_name, cls.FileData[short_name].Events]
                else:
                    d_pairs[unhashed_name] = [hash_name, cls.FileData[short_name].Events]

        return d_pairs
                


class WemXmlObject:
    """
    Class containing wem data found in XML files.
    """
    def __init__(self, e_xml_file_object, event = None):
        self.ShortName = e_xml_file_object.find("ShortName").text.split(".")[0]
        self.Files = {
            e_xml_file_object.attrib["Id"] : e_xml_file_object.find("Path").text.split(".")[0]
        }
        self.Events = []
        if event != None:
            self.Events.append(event)


class wemDidx:
    def __init__(self, wemId, wemOffset, wemSize):
        self.WemId = wemId
        self.WemOffset = wemOffset
        self.WemSize = wemSize
    def __init__(self, f):
        self.WemId = int.from_bytes(f.read(4), byteorder='little')
        self.WemOffset = int.from_bytes(f.read(4), byteorder='little')
        self.WemSize = int.from_bytes(f.read(4), byteorder='little')
    def __str__(self):
        return '\t'.join(str(item) for item in [self.WemId, self.WemOffset, self.WemSize])

class BnkObject:
    def __init__(self, fileName):
        self.Didx = []
        self.Data = {}
        self.Sec = {}
        with open(fileName, 'rb') as f:
            if f.read(4).decode("utf-8") != "BKHD":
                raise Exception(f" {fileName} did not parse correctly. Lacks BKHD")
            self.BKHD = f.read(int.from_bytes(f.read(4), byteorder='little'))
            #f.seek(int.from_bytes(f.read(4), byteorder='little')+8)

            if f.read(4).decode("utf-8") != "DIDX":
                return
                #raise Exception(f" {fileName} did not parse correctly. Lacks DIDX")

            wemCount = int(int.from_bytes(f.read(4), byteorder='little')/12)
            self.Didx = [wemDidx(f) for wemIdx in range(0, wemCount)] 

            if f.read(4).decode("utf-8") != "DATA":
                raise Exception(f" {fileName} did not parse correctly. Lacks DATA")
            dataSize = int(int.from_bytes(f.read(4), byteorder='little'))
            dataOffset = f.tell()
            self.Data = {}
            for didx in self.Didx:
                f.seek(dataOffset + didx.WemOffset)
                self.Data[didx.WemId] = f.read(didx.WemSize)

            while True:
                secType = f.read(4).decode("utf-8")
                if secType == "":
                    break
                self.Sec[secType] =  f.read(int.from_bytes(f.read(4), byteorder='little'))

    def build(self, fileName):
        with open(fileName, 'wb') as f:
            f.write("BKHD".encode())
            f.write((len(self.BKHD)).to_bytes(4, byteorder='little'))
            f.write(self.BKHD)

            f.write("DIDX".encode())
            f.write((len(self.Didx)*12).to_bytes(4, byteorder='little'))
            b_DataStream = bytearray()
            for wemId in self.Data:
                if len(b_DataStream) % 16 != 0:
                    b_DataStream += bytes(16-len(b_DataStream) % 16)
                f.write((int(wemId)).to_bytes(4, byteorder='little'))
                f.write((len(b_DataStream)).to_bytes(4, byteorder='little'))
                f.write((len(self.Data[wemId])).to_bytes(4, byteorder='little'))
                b_DataStream += self.Data[wemId]

            f.write("DATA".encode())
            f.write(len(b_DataStream).to_bytes(4, byteorder='little'))
            f.write(b_DataStream)

            for secName in self.Sec:
                f.write(secName.encode())
                f.write(len(self.Sec[secName]).to_bytes(4, byteorder='little'))
                f.write(self.Sec[secName])


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def extract_file_names(path, ext = None):
    """Lazy function to stop me repeating the same ugly code"""
    if ext == None:
        return [file for file in os.listdir(path) if os.path.isfile(os.path.join(path, file))]
    else:
        return [file for file in os.listdir(path) if os.path.isfile(os.path.join(path, file)) and file.split(".")[1] == ext]         

d_character_pairs = {
    "A" : "Pit Droid",
    "B" : "Pit Droid",
    "C" : "Pit Droid",
    "D" : "Pit Droid",
    "E" : "Pit Droid",
    "F" : "Pit Droid",
    "G" : "Pit Droid",
    "020b Zk8880" : "Purge Trooper 1",
    "030b Er0198" : "Stormtrooper 5",
    "Am1529" : "Stormtrooper 1",
    "B1 Professional B" : "B1 Professional",
    "B1c" : "B1 Default",
    "B1c B" : "B1 Default",
    "B2 M" : "B2 Male",
    "B2 F" : "B2 Female",
    "Ba3412" : "Stormtrooper 2",
    "Bd1-002" : "BD1",
    "Bevan" : "ISB Agent 1",
    "Bfett" : "Boba Fett",
    "Bode Exert" : "Bode",
    "Dbode" : "Bode",
    "Boxy" : "Bounty Hunter 1",
    "Brav" : "Bravo",
    "Brothera" : "Jedha Brother 1",
    "Brothere" : "Jedha Brother 2",
    "Cal-001" : "Cal",
    "Cockpitenter Cal" : "Cal",
    "Crawl A Cal" : "Cal",
    "Crawl B Cal" : "Cal",
    "Crawl C Cal" : "Cal",
    "Enc Jedambush Cal" : "Cal",
    "Enc Jedambush Fail Cal" : "Cal",
    "Enc Jedambush Success Cal" : "Cal",
    "Entrance Cal" : "Cal",
    "Find device Cal" : "Cal",
    "Forcepush Cal" : "Cal",
    "Find device Bd1" : "Bd1",
    "Carlyle" : "ISB Agent 2",
    "Bold Jedi" : "Jedi Bold",
    "Cautious Jedi" : "Jedi Cautious",
    "Djedi" : "Jedi Dead",
    "Checkpoint Officer" : "Stormtrooper Checkpoint Officer",
    "Cordova" : "Eno Cordova",
    "Cow Lucrehulkexitcrash" : "Temp Rehersals",
    "Cow Observatoryfight Clash" : "Temp Rehersals",
    "Cow Rayvisleaves Part2" : "Temp Rehersals",
    "Cow Spires Goldenecho Daganhouse Preechogasp Cal" : "Temp Rehersals",
    "Cow Zenointro Flbk" : "Temp Rehersals",
    "Gendaiintro Armor" : "Temp Rehersals",
    "Cr6520" : "Stormtrooper 3",
    "Davis" : "Bedlam Raider Male 1",
    "Dt9811" : "Stormtrooper 4",
    "Dylok" : "Bounty Hunter 2",
    "Eileen" : "Elieen",
    "Er0198" : "Stormtrooper 5",
    "Enc Jedambush Er0198" : "Stormtrooper 5",
    "Enc Jedambush Fail Er0198" : "Stormtrooper 5",
    "Enc Jedambush Success Er0198" : "Stormtrooper 5",
    "Fb4528" : "Purge Trooper 2",
    "Gn7173" : "Stormtrooper 6",
    "Gpadawan" : "Jedi Padawan",
    "Greez-001":"Greez",
    "Holecrawl A Cal":"Cal",
    "Holecrawl B Cal":"Cal",
    "Holecrawl C Forcepush Cal":"Cal",
    "Impoff":"Stormtrooper Impoff",
    "Isb":"ISB Agent Generic",
    "Jaren":"Bounty Hunter 3",
    "Jed Claustro Startled Cal":"Cal",
    "Jed Escapeintro":"Temp Rehersals",
    "Jo4879":"Purge Trooper 3",
    "Jones":"Bedlam Raider Male 2",
    "Leap Cal":"Cal",
    "Lyndon":"Bedlam Raider Male 3",
    "Magna":"Magnaguard",
    "Magna2":"Magnaguard",
    "Martus":"Bounty Hunter 4",
    "Master":"JFO Recap",
    "Ninthsis":"Ninth Sister",
    "Pierce":"Bedlam Raider Male 4",
    "Pjedi":"Jedi P",
    "Prospector":"Prospectors",
    "Pt0008":"Purge Trooper 4",
    "Raquel":"Bedlam Raider Female 1",
    "Reena":"Bounty Hunter 5",
    "Roma-001":"Roma",
    "Roma-002":"Roma",
    "Saberequip Cal" : "Cal",
    "Santarir" : "Santari",
    "Scroobius" : "Bounty Hunter 6",
    "Secdroid" : "Kx-Security Droid Male",
    "Secdroid F" : "Kx-Security Droid Female",
    "Secdroidm" : "Kx-Security Droid Male",
    "Sensejan" : "Senator Sejan",
    "Silenc Halfsecond" : "Silence",
    "Silence 1point5sec" : "Silence",
    "Silence 1sec" : "Silence",
    "Silence Point5sec" : "Silence",
    "Sisteri" : "Jedha Sister 1",
    "Sistern" : "Jedha Sister 2",
    "Sistertaske" : "Jedha Sister 3",
    "Sky" : "Bedlam Raider Female 2",
    "Squeeze Cal" : "Cal",
    "Stand Cal" : "Cal",
    "Tan Duel Phase1 Bode Phantommenace" : "Temp Rehersals",
    "Thrownfromcave-001" : "Stormtrooper Cave",
    "Thrownfromcave-002" : "Stormtrooper Cave",
    "Thrownfromcave-003" : "Stormtrooper Cave",
    "Trilla" : "JFO Trilla",
    "Sorc Tormo" : "JFO Sorc Tormo",
    "Prauf" : "JFO Prauf",
    "Tumble Cal" : "Cal",
    "Zk8880" : "Purge Trooper 1",
    "Vader" : "Darth Vader",
    "Vario" : "Bounty Hunter 7",
    "Vet" : "Coruscant Veteran",
    "Vo Sys Droid Tar Alert Drown Bd1 Sfxlayer01 Cs Inv1st" : "Unknown",
    "Vo Sys Droid Tar Alert Drown Bd1 Sfxlayer01 Cs Root" : "Unknown",
    "Vo Sys Droid Tar Alert Drown Bd1 Sfxlayer02 Ds Inv1st" : "Unknown",
    "Vo Sys Droid Tar Alert Drown Bd1 Sfxlayer02 Ds Root" : "Unknown",
    "Vo Sys Droid Tar Alert Drown Bd1 Sfxlayer03 Fs Root" : "Unknown",
    "Vo Sys Droid Tar Alert Drown Bd1 Sfxlayer03 Fsinv1st" : "Unknown",
    "Vo Sys Droid Tar Alert Drown Bd1 Sfxlayer04 Gs Inv1st" : "Unknown",
    "Vo Sys Droid Tar Alert Drown Bd1 Sfxlayer04 Gs Root" : "Unknown",
    "Zeik" : "Bedlam Raider Male 5",
    "Zna4" : "Zee",
}
@click.command()
@click.option("-i", "--input", prompt="Enter the audio source directory.", help="The name of the audio folder containing all of the raw extracted wems, bnks, xml and json from the game.")
@click.option("-o", "--output", prompt="Enter the output directory.", help="The name of the folder where all the named extracted audio should be placed after running the script.")
@click.option("-l", "--locres", help="The path of the game.locres file exported as a json (using Fmodel). For voice lines this will result in the output csv containing subtitles matching each line. Leave this blank if you don't want to do this.")
def extract_wems(input, output, locres):
    """This command is designed to extract and rename all of the game's wems with readable plain text names e.g. "308125441.wem" -> "vo_eff_dodge_lrg_002_rayvis.wem"."""
    input_files = extract_file_names(input)
    unused_wem_files = [file for file in input_files if file.split(".")[-1] == "wem"]
    input_xml_files = [file for file in input_files if file.split(".")[-1] == "xml"]

    locresDict = {}
    if locres != None:
        with open(locres, 'r') as locresFile:
            locresJson = json.load(locresFile)
            for locreId in locresJson["RAP"].keys():
                locresDict["_".join(locreId.split("_", 2)[2:])] = locresJson["RAP"][locreId]

    if not os.path.exists(output):
         os.makedirs(output)
    with open(os.path.join(output, "ExportedWems.csv"), 'w', encoding='UTF8', newline='') as csvFile:
        csvWriter = csv.writer(csvFile)
        csvWriter.writerow(["Id", "Bnk File", "Relative Path", "Export Path", "Character", "Locres Subtitle"])
        for xml_short_name in input_xml_files:
            s_bnkFullName = os.path.join(input,xml_short_name.replace(".xml", ".bnk"))
            if not os.path.isfile(s_bnkFullName):
                continue
            o_bnk = BnkObject(s_bnkFullName)
            d_bnkOnlyWems = copy.deepcopy(o_bnk.Data)
            o_xml_file = BnkXmlObject(os.path.join(input, xml_short_name))
            for name_pair in o_xml_file.create_hash_pairs(input).items():
                if (xml_short_name.startswith("vo_") or xml_short_name.startswith("VO")):
                    character_name = []
                    for vo_name_substring in reversed(name_pair[1][0].split("_")):
                        if vo_name_substring.isdigit():
                            break
                        elif vo_name_substring != "spj" and vo_name_substring != "sp":
                            character_name.insert(0, vo_name_substring.capitalize())

                    if len(character_name) == 0:
                        character_name = ["No Character"]
                    character_name = ' '.join(character_name).rstrip()

                    for common_type in ["Cal", "Ui", "Prospector", "Bd1"]:
                        if (character_name.startswith(common_type + " ")):
                            character_name = common_type
                    if character_name in d_character_pairs:
                        character_name = d_character_pairs[character_name]
                    
                    wem_relative_path = os.path.join(character_name, xml_short_name.split(".")[0],name_pair[1][0] + ".wem")
                    wem_paste_name = os.path.join(output, wem_relative_path)

                    subtitle = "#N/A"
                    if locresDict != None:
                        if name_pair[1][0] in locresDict:
                                subtitle = locresDict[name_pair[1][0]]
                        if subtitle == "#N/A":
                            if name_pair[1][1][0] in locresDict:
                                subtitle = locresDict[name_pair[1][1][0]]
                    csvWriter.writerow([name_pair[1][0], xml_short_name.split(".")[0], wem_relative_path, wem_paste_name, character_name, subtitle])
                else:
                    wem_relative_path = os.path.join(xml_short_name.split(".")[0],name_pair[1][0] + ".wem")
                    wem_paste_name = os.path.join(output, wem_relative_path)
                    csvWriter.writerow([name_pair[1][0], xml_short_name.split(".")[0], wem_relative_path, wem_paste_name, "#N/A", "#N/A"])


                if os.path.exists(os.path.join(input, name_pair[0] + ".wem")):
                    if not os.path.exists(os.path.dirname(wem_paste_name)):
                        os.makedirs(os.path.dirname(wem_paste_name))

                    if (name_pair[0] + ".wem" in unused_wem_files):
                        unused_wem_files.remove(name_pair[0] + ".wem" )

                    if int(name_pair[0]) in d_bnkOnlyWems:
                        del d_bnkOnlyWems[int(name_pair[0])]
                    shutil.copy(os.path.join(input, name_pair[0] + ".wem"), wem_paste_name)

            for i_bnkOnlyWem in d_bnkOnlyWems:
                wem_relative_path = os.path.join(xml_short_name.split(".")[0],"HashedWem_" + str(i_bnkOnlyWem) + ".wem")
                wem_paste_name = os.path.join(output, wem_relative_path)
                csvWriter.writerow(["HashedWem_" + str(i_bnkOnlyWem), xml_short_name.split(".")[0], wem_relative_path, wem_paste_name, "#N/A", "#N/A"])
                if not os.path.exists(os.path.dirname(wem_paste_name)):
                    os.makedirs(os.path.dirname(wem_paste_name))
                with open(wem_paste_name, 'wb') as f: 
                    f.write(d_bnkOnlyWems[i_bnkOnlyWem])
    for wem_short_name in unused_wem_files:
        wem_paste_name = os.path.join(output, "UnusedWems",wem_short_name)

        if not os.path.exists(os.path.dirname(wem_paste_name)):
            os.makedirs(os.path.dirname(wem_paste_name))

        shutil.copy(os.path.join(input, wem_short_name), wem_paste_name)
    print("Renaming Completed")

@click.command()
@click.option("-w", "--wemfolder", prompt="Enter the directory containing all of the wem files you wish hashed.", help="The name of the audio folder containing all of the wem files you wish hashed. For SFX you will need the .wems to be contained in subdirectories with names which match the name of the .bnk they came from.")
@click.option("-b", "--bnkfolder", prompt="Enter the directory containing the extracted base game .bnks and their matching xml and json files.", help="The name of the audio folder containing the extracted base game .bnks and their matching xml and json files.")
@click.option("-o", "--output", prompt="Enter the output directory", help="The name of the folder where all the rehashed wems should be placed after running the script.")
@click.option("-rs", "--removesuffix", help="Remove suffix of generated wem files when importing. E.G \"vo_cin_011000_cor_ninthsister_85652_cal_3F75BDB9.wem\" becomes \"vo_cin_011000_cor_ninthsister_85652_cal.wem\"")
def reimport_wems(wemfolder, bnkfolder, output, removesuffix):
    """This command is designed to take modified .wem files and rename them from the plain text representations to the hashes the game uses e.g. "vo_eff_dodge_lrg_002_rayvis.wem" =>  "308125441.wem". This will also modify .bnks to modify precache .wems."""
    unmatched_wem_files = extract_file_names(wemfolder, "wem")
    xml_files = extract_file_names(bnkfolder, "xml")

    l_bnks_todo = []
    for bnk_short_name in next(os.walk(wemfolder))[1]:
        l_bnks_todo.append(bnk_short_name)
    for xml_short_name in xml_files:
        if xml_short_name.startswith("VO") and xml_short_name[:-4] not in l_bnks_todo:
            l_bnks_todo.append(xml_short_name[:-4])
    
    l_completed_bnks = []
    if not os.path.exists(output):
         os.makedirs(output)

    d_Updated_Wems = {}
    
    if removesuffix is not None:
        if not removesuffix.startswith("_"):
                removesuffix = "_" + removesuffix
    else:
        removesuffix = "_3F75BDB9"

    for idx, wem_name in enumerate(unmatched_wem_files):
        unmatched_wem_files[idx] = wem_name.replace(removesuffix, '')
    
    print("\n\nCopying Wems and rebuilding BNKs:\n")
    for bnk_short_name in l_bnks_todo:
        if bnk_short_name + ".xml" not in xml_files:
            print(f"Warning: Could not find a BNK by the name of {bnk_short_name} in directory {bnkfolder}")
            continue
        else:
            l_completed_bnks.append(bnk_short_name + ".xml")

        s_bnkFullName = os.path.join(bnkfolder, bnk_short_name + ".bnk")
        if not os.path.isfile(s_bnkFullName):
            print(f"Warning: Could not find a BNK by the name of {bnk_short_name} in directory {bnkfolder}")
            continue

        o_bnk = BnkObject(s_bnkFullName)
        o_xml_file = BnkXmlObject(os.path.join(bnkfolder, bnk_short_name + ".xml"))

        l_wem_files = {}
        s_bnk_folder = os.path.join(wemfolder, bnk_short_name)
        def get_wems(folder, isRoot):
            for root, dirs, files in os.walk(folder, topdown=False):
                for file in files:
                    if file.endswith(".wem"):
                        os.rename(os.path.join(root, file), os.path.join(root, file.replace(removesuffix, '')))
                        l_wem_files[os.path.join(root, file.replace(removesuffix, ''))[len(folder)+1:-4]] = [os.path.join(root, file.replace(removesuffix, '')), isRoot]
        s_bnk_folder = os.path.join(wemfolder, bnk_short_name)
        if os.path.exists(s_bnk_folder):
            get_wems(s_bnk_folder, False)
        if bnk_short_name.startswith("VO"):
            get_wems(wemfolder, True)
        
        b_BnkNeedsUpdating = False
        for name_pair in o_xml_file.create_hash_pairs(bnkfolder, False).items():
            if name_pair[0] in l_wem_files:
                s_named_wem_path = l_wem_files[name_pair[0]][0]
                if l_wem_files[name_pair[0]][1] == True:
                    s_wem_shortname = os.path.basename(s_named_wem_path)
                    if s_wem_shortname in unmatched_wem_files:
                        unmatched_wem_files.remove(s_wem_shortname)

                i_wem_hash = int(name_pair[1][0])
                if i_wem_hash not in d_Updated_Wems:
                    d_Updated_Wems[i_wem_hash] = s_named_wem_path

                if i_wem_hash in o_bnk.Data:
                    b_BnkNeedsUpdating = True
                    with open(s_named_wem_path, 'rb') as f:
                        o_bnk.Data[i_wem_hash] = f.read(len(o_bnk.Data[i_wem_hash]))
                shutil.copy(s_named_wem_path, os.path.join(output, name_pair[1][0] + ".wem"))
                del l_wem_files[name_pair[0]]

        for unmatched_wem in l_wem_files:
            b_added = False
            if unmatched_wem.startswith("HashedWem_"):
                wem_hash = int(unmatched_wem[10:])
                if wem_hash in o_bnk.Data:
                    b_BnkNeedsUpdating = True
                    b_added = True
                    with open(s_named_wem_path, 'rb') as f:
                        o_bnk.Data[wem_hash] = f.read(len(o_bnk.Data[wem_hash]))
            if not b_added:
                if l_wem_files[unmatched_wem][1] == False:
                    print(f"Warning: Could not find matching wem for {unmatched_wem}.wem in {bnk_short_name}.bnk")


        if b_BnkNeedsUpdating == True:
            print(f"Rebuilding {bnk_short_name}")
            o_bnk.build(os.path.join(output,bnk_short_name +  ".bnk"))
  
    print("\n\nChecking if other BNKs need updating.\n")
    for xml_short_name in xml_files:
        bnk_short_name = xml_short_name.replace(".xml", ".bnk")
        s_bnkFullName = os.path.join(bnkfolder,bnk_short_name)
        if not os.path.isfile(s_bnkFullName) or xml_short_name in l_completed_bnks:
            continue
        o_bnk = BnkObject(s_bnkFullName)
        
        b_SharedWems = 0
        for name_pair in d_Updated_Wems.items():
            if name_pair[0] in o_bnk.Data:
                b_SharedWems+= 1
                with open(name_pair[1], 'rb') as f:
                    o_bnk.Data[name_pair[0]] = f.read(len(o_bnk.Data[name_pair[0]]))
                    #print(name_pair[1])

        if b_SharedWems != 0:
            print(f"Rebuilding {bnk_short_name} as it contains precache of {b_SharedWems} modified .wems")
            o_bnk.build(os.path.join(output,bnk_short_name))

    for unmatched_wem in unmatched_wem_files:
        print(f"Warning: Could not find matching wem for {unmatched_wem}")

    print("\n\nWem reimporting complete\n")
    

mycommands.add_command(extract_wems)
mycommands.add_command(reimport_wems)
if __name__ == "__main__":
    mycommands()