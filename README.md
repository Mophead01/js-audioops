# js-audioops

Python script for handling the extraction/renaming and reimporting of wem files from Jedi Survivor. Please refer to https://docs.google.com/document/d/1mci_76-3gRF7njtZBWi51noEId3u_fGDG--1XA-FF8s/edit?usp=sharing for guideance on how to use.

# extract-wems
This command is designed to extract and rename all of the game's wems with readable plain text names e.g. "308125441.wem" -> "vo_eff_dodge_lrg_002_rayvis.wem".

Options:
  -i, --input TEXT   The name of the audio folder containing all of the raw
                     extracted wems, bnks, xml and json from the game.
  -o, --output TEXT  The name of the folder where all the named extracted
                     audio should be placed after running the script.
  -l, --locres TEXT  The path of the game.locres file exported as a json
                     (using Fmodel). For voice lines this will result in the
                     output csv containing subtitles matching each line. Leave
                     this blank if you don't want to do this.
  --help             Show this message and exit.
  
# reimport-wems
This command is designed to take modified .wem files and rename them from the plain text representations to the hashes the game uses e.g. "vo_eff_dodge_lrg_002_rayvis.wem" =>  "308125441.wem". This will also modify .bnks to modify precache .wems.

Options:
  -w, --wemfolder TEXT      The name of the audio folder containing all of the
                            wem files you wish hashed. For SFX you will need
                            the .wems to be contained in subdirectories with
                            names which match the name of the .bnk they came
                            from.
  -b, --bnkfolder TEXT      The name of the audio folder containing the
                            extracted base game .bnks and their matching xml
                            and json files.
  -o, --output TEXT         The name of the folder where all the rehashed wems
                            should be placed after running the script.
  -rs, --removesuffix TEXT  Remove suffix of generated wem files when
                            importing. E.G "vo_cin_011000_cor_ninthsister_8565
                            2_cal_3F75BDB9.wem" becomes
                            "vo_cin_011000_cor_ninthsister_85652_cal.wem"
  --help                    Show this message and exit.
