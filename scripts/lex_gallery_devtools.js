// lex_gallery_devtools.js
// Paste into Firefox DevTools console while logged into Lexicanum with a valid
// Cloudflare clearance cookie. Visit any ageofsigmar.lexicanum.com page first
// (e.g. https://ageofsigmar.lexicanum.com/wiki/List_of_units).
//
// Scrapes /wiki/Gallery:<UnitTitle> pages and downloads miniature photos,
// filtering out the warscroll/infobox art (`full_image_filename` per unit).
//
// Emits two downloads:
//   - lex_gallery_images.zip      (one or more images per unit, named
//                                   <slug>__<index>.<ext>)
//   - lex_gallery_manifest.json   (slug -> [{filename, source_url,
//                                            was_filtered_warscroll}])
//
// Sourced from scripts/cache/lexicanum_manifest.json (588 units).

(async () => {
  // --------------------------------------------------------------- UNITS
  // Each entry: [slug, title, full_image_filename]
  // full_image_filename is the basename of `full_image_url` from the manifest
  // and is used to filter out the warscroll infobox art from gallery hits.
  const UNITS_JSON = '[["beastlord","Beastlord","Beastlord_01.jpeg"],["bestigor","Bestigor","Bestigor.jpg"],["centigor","Centigor","Centigor_M01.jpeg"],["gor","Gor","Gor_01.jpg"],["great-bray-shaman","Great Bray-Shaman","Great_Bray-Shaman_01.jpg"],["tuskgor-chariot","Tuskgor Chariot","Tuskgor_Chariot_M01.jpg"],["tzaangor","Tzaangor","Tzaangor_01.png"],["tzaangor-enlightened","Tzaangor Enlightened","Tzaangor_Enlightened_M01.jpg"],["tzaangor-shaman","Tzaangor Shaman","Tzaangor_shaman_02.jpg"],["tzaangor-skyfire","Tzaangor Skyfire","Tzaangor_Skyfire_M01.jpg"],["ungor","Ungor","Ungor_M01.jpg"],["ungor-raider","Ungor Raider","Ushkor_shooting_an_arrow_01.jpg"],["daemon-prince","Daemon Prince","Be\'lakor_02.jpg"],["fury","Fury","Fury_M04.jpg"],["gaunt-summoner-of-tzeentch","Gaunt Summoner of Tzeentch","Pict_Gaunt_Summoner_of_Tzeentch.jpg"],["mutalith-vortex-beast","Mutalith Vortex Beast","Pict_Mutalith_Vortex_Beast.jpg"],["slaughterbrute","Slaughterbrute","Slaughterbrute_01.jpg"],["soul-grinder","Soul Grinder","Soul_Grinder_M01.jpg"],["karanak","Karanak","Karanak_02.jpg"],["skarbrand","Skarbrand","Skarbrand_profile_01.png"],["skulltaker","Skulltaker","Skulltaker_vs_Ironjawz_01.png"],["beast-of-nurgle","Beast of Nurgle","Beasts_of_Nurgle_01.jpg"],["cankerborn","Cankerborn","Cankerborn_M01.jpg"],["great-unclean-one","Great Unclean One","Pict_Great_Unclean_One.jpg"],["nurgling","Nurgling","Pict_Nurgling.jpg"],["plague-drone-of-nurgle","Plague Drone of Nurgle","Plague_Drone_M01.jpg"],["plaguebearer-of-nurgle","Plaguebearer of Nurgle","Plaguebearer_02.jpg"],["poxbringer","Poxbringer","Poxbringer_M01.jpg"],["spoilpox-scrivener","Spoilpox Scrivener","Poxbringer_M01.jpg"],["sloppity-bilepiper","Sloppity Bilepiper","Poxbringer_M01.jpg"],["blue-horrors-of-tzeentch","Blue Horrors of Tzeentch","Horrors_of_Tzeentch_01.png"],["brimstone-horrors-of-tzeentch","Brimstone Horrors of Tzeentch","Horrors_of_Tzeentch_01.png"],["burning-chariot-of-tzeentch","Burning Chariot of Tzeentch","Herald_of_Tzeentch_03.jpg"],["exalted-flamer-of-tzeentch","Exalted Flamer of Tzeentch","Flamer_01.png"],["flamer-of-tzeentch","Flamer of Tzeentch","Flamer_01.png"],["herald-of-tzeentch","Herald of Tzeentch","Herald_of_Tzeentch_02.jpg"],["lord-of-change","Lord of Change","Pict_Lord_of_Change.jpg"],["pink-horror-of-tzeentch","Pink Horror of Tzeentch","Horrors_of_Tzeentch_01.png"],["screamer-of-tzeentch","Screamer of Tzeentch","Pict_Screamer_of_Tzeentch.jpg"],["bladebringer","Bladebringer","Herald_of_Slaanesh_01.jpg"],["contorted-epitome","Contorted Epitome","Herald_of_Slaanesh_01.jpg"],["daemonette-of-slaanesh","Daemonette of Slaanesh","Daemonette_04.jpeg"],["fiend-of-slaanesh","Fiend of Slaanesh","Fiend_of_Slaanesh_01.jpg"],["infernal-enrapturess","Infernal Enrapturess","Herald_of_Slaanesh_01.jpg"],["keeper-of-secrets","Keeper of Secrets","Daemons_of_Slaanesh_vs_Daughters_of_Khaine_01.jpg"],["seeker-of-slaanesh","Seeker of Slaanesh","Seekers_of_Slaanesh_02.png"],["viceleader","Viceleader","Herald_of_Slaanesh_01.jpg"],["gutter-runner","Gutter Runner","Gutter_Runner_M01.jpg"],["night-runner","Night Runner","Night_Runners_01.jpg"],["deathmaster","Deathmaster","Skaven_Deathmaster_01.jpg"],["deathrunner","Deathrunner","Deathrunner_01.jpg"],["verminlord-deceiver","Verminlord Deceiver","Pestilens_01.png"],["varanguard","Varanguard","Archaon_leading_the_Varanguard_01.jpeg"],["blissbarb-archer","Blissbarb Archer","Blissbarb_Archer_01.jpg"],["blissbarb-seeker","Blissbarb Seeker","Slaanesh_Sybarites_02.jpg"],["hellstrider-of-slaanesh","Hellstrider of Slaanesh","Hellstriders_01.png"],["lord-of-hubris","Lord of Hubris","Lord_of_Hubris_M01.jpg"],["lord-of-pain","Lord of Pain","Lord_of_Pain_01.png"],["myrmidesh-painbringer","Myrmidesh Painbringer","Glutos_02.jpg"],["shardspeaker-of-slaanesh","Shardspeaker of Slaanesh","Shardspeaker_01.jpg"],["slaangor-fiendblood","Slaangor Fiendblood","Slaangor_01.png"],["slickblade-seeker","Slickblade Seeker","Slaanesh_Sybarites_02.jpg"],["symbaresh-twinsoul","Symbaresh Twinsoul","Glutos_02.jpg"],["garrek%27s-reavers","Garrek\'s Reavers","Garrek\'s_Reavers_-_Underworlds_Icon.png"],["gorechosen-of-dromm","Gorechosen of Dromm","Gorechosen_of_Dromm_-_Underworlds_Icon.png"],["kamandora%27s-blades","Kamandora\'s Blades","Kamandora\'s_Blades_-_Underworlds_Icon.png"],["korghos-khul","Korghos Khul","Lord_of_Khorne_M01.jpg"],["magore%27s-fiends","Magore\'s Fiends","Magore\'s_Fiends_-_Underworlds_Icon.png"],["riptooth","Riptooth","Riptooth_M01.jpg"],["scyla-anfingrimm","Scyla Anfingrimm","Scyla_vs_Grey_Seer_01.png"],["skarr-bloodwrath","Skarr Bloodwrath","Skarr_M01.jpg"],["valkia","Valkia","Profile_Valkia.jpg"],["grey-seer","Grey Seer","Grey_Seer_01.jpg"],["screaming-bell","Screaming Bell","Screaming_Bell_01.jpg"],["verminlord-warpseer","Verminlord Warpseer","Pestilens_01.png"],["chaos-gargant","Chaos Gargant","Chaos_Gargant_01.jpg"],["chaos-warhound","Chaos Warhound","Chaos_Warhound_M03.jpg"],["chimera","Chimera","Chimera_02.png"],["cockatrice","Cockatrice","Cockatrice_M01.jpg"],["jabberslythe","Jabberslythe","Jabberslythe_M01.jpg"],["razorgor","Razorgor","Razorgor_M01.jpg"],["brood-terror","Brood Terror","Brood_Terror_M01.jpg"],["giant-rat","Giant Rat","Rat_Swarm_01.jpg"],["hell-pit-abomination","Hell Pit Abomination","Hell_Pit_Abomination_01.jpg"],["master-moulder","Master Moulder","Master_Moulder_M01.jpg"],["packmaster","Packmaster","Packmaster_M01.jpg"],["rat-ogor","Rat Ogor","Rat_Ogor_03.jpg"],["rat-swarm","Rat Swarm","Rat_Swarm_01.jpg"],["stormfiend","Stormfiend","Stormfiend_01.jpg"],["blight-templar","Blight Templar","Blight_Templar_M01.jpg"],["harbinger-of-decay","Harbinger of Decay","Harbinger_of_Decay_01.jpg"],["lord-of-afflictions","Lord of Afflictions","Lord_of_Afflictions_01.jpg"],["lord-of-blights","Lord of Blights","Lord_of_Afflictions_01.jpg"],["lord-of-plagues","Lord of Plagues","Lord_of_Afflictions_01.jpg"],["pestigor","Pestigor","Shaman_Foulhoof_01.jpg"],["pox-wretch","Pox-wretch","Pox-wretch_M01.jpg"],["pusgoyle-blightlord","Pusgoyle Blightlord","Pusgoyle_Blightlord_01.jpg"],["putrid-blightking","Putrid Blightking","Putrid_Blightking_01.jpeg"],["rotbringer-sorcerer","Rotbringer Sorcerer","Rotbringer_Sorcerer_01.jpg"],["rotmire-creed","Rotmire Creed","Witherlord.jpg"],["rotsword","Rotsword","Rotsword_01.jpg"],["sloven-knight","Sloven Knight","Sloven_Knight_M01.jpg"],["plague-censer-bearer","Plague Censer Bearer","Plague_Censer_Bearer_01.jpg"],["plague-furnace","Plague Furnace","Plague_Furnace_01.jpg"],["plague-monk","Plague Monk","Plague_Monk_01.jpg"],["plague-priest","Plague Priest","Plague_Priest_01.jpg"],["plagueclaw","Plagueclaw","Plagueclaw_01.jpg"],["verminlord-corruptor","Verminlord Corruptor","Pestilens_01.png"],["arch-warlock","Arch-Warlock","Arch-Warlock_01.png"],["doom-flayer","Doom-Flayer","Doom-Flayer_M03.jpg"],["doomwheel","Doomwheel","Doomwheel_02.jpg"],["acolyte-globadier","Acolyte Globadier","Skryre_Acolyte_01.png"],["ratling-warpblaster","Ratling Warpblaster","Ratling_Warpblaster_M01.jpg"],["warlock-bombardier","Warlock Bombardier","Warlock_Bombardier_01.jpg"],["warlock-engineer","Warlock Engineer","Warlock_Engineer_M01.jpg"],["warlock-galvaneer","Warlock Galvaneer","Warlock_Galvaneer_M01.jpg"],["warp-lightning-cannon","Warp Lightning Cannon","Warp_Lightning_Cannon_M02.jpg"],["warp-grinder","Warp-Grinder","Warp-Grinder_M01.jpg"],["warpspark-weapon-battery","Warpspark Weapon Battery","Skryre_Weapon_Team_01.jpg"],["warplock-jezzail","Warplock Jezzail","Skryre_Weapon_Team_01.jpg"],["centaurion-marshal","Centaurion Marshal","Centaurion_Marshal_M01.jpg"],["corvus-cabal","Corvus Cabal","Chimera_01.png"],["cypher-lords","Cypher Lords","Cypher_Lords_M01.jpg"],["chaos-legionnaires","Chaos Legionnaires","Chaos_Legionnaires_M01.jpg"],["chaos-spawn","Chaos Spawn","Chaos_Spawn_01.jpg"],["fomoroid-crusher","Fomoroid Crusher","Fomoroid_Crusher_M01.jpg"],["horns-of-hashut","Horns of Hashut","Ruinator_Alpha.jpg"],["iron-golem","Iron Golem","Warcry_Boxcover.jpg"],["mindstealer-sphiranx","Mindstealer Sphiranx","Mindstealer_Sphiranx_01.jpg"],["ogroid-myrmidon","Ogroid Myrmidon","Ogroid_Myrmidon_01.jpg"],["ogroid-theridons","Ogroid Theridons","Ogroid_Theridon_M01.jpg"],["scions-of-the-flame","Scions of the Flame","Blazing_Lord_vs_Shadowstalkers.jpg"],["spire-tyrants","Spire Tyrants","Spire_Tyrants_M01.jpg"],["splintered-fang","Splintered Fang","Trueblood_M01.jpg"],["tarantulos-brood","Tarantulos Brood","Darkoath_Savagers_-_Tarantulos_Brood.jpg"],["raptoryx","Raptoryx","Raptoryx_M01.jpg"],["untamed-beasts","Untamed Beasts","Iron_Golems_vs_Untamed_Beasts_01.jpg"],["unmade","Unmade","Iron_Golems_vs_Unmade_01.jpg"],["dragon-ogor","Dragon Ogor","Dragon_Ogor_01.jpeg"],["dragon-ogor-shaggoth","Dragon Ogor Shaggoth","Dragon_Ogor_01.jpeg"],["curseling","Curseling","Tzeentch_Arcanites_vs_Freeguild_01.png"],["fatemaster","Fatemaster","Fatemaster.jpeg"],["jade-obelisk","Jade Obelisk","Jade_Obelisk_vs_Hunters_of_Huanchi.jpg"],["kairic-acolyte","Kairic Acolyte","Kairic_Acolyte_01.png"],["magister","Magister","Battlemage_vs_Magister_01.jpeg"],["ogroid-thaumaturge","Ogroid Thaumaturge","Pict_Ogroid_Thaumaturge.jpg"],["clanrat","Clanrat","Clanrat_Art_01.png"],["clawlord","Clawlord","Clawlord_on_Gnaw-Beast_01.jpg"],["stormvermin","Stormvermin","Stormvermin_02.jpg"],["verminlord-warbringer","Verminlord Warbringer","Pestilens_01.png"],["bullgor-warrior","Bullgor","Pict_Bullgor.jpg"],["cygor","Cygor","Cygor_01.jpg"],["doombull","Doombull","Doombull_01.jpeg"],["ghorgon","Ghorgon","Pict_Ghorgon.jpg"],["chaos-chariot","Chaos Chariot","Chaos_Chariot.jpg"],["chaos-chosen","Chaos Chosen","Chaos_Chosen_M02.jpg"],["chaos-gorebeast-chariot","Chaos Gorebeast Chariot","Chaos_Chariot.jpg"],["chaos-knight","Chaos Knight","Chaos_Knight_M01.jpg"],["chaos-lord","Chaos Lord","Chaos_Lord_on_Daemonic_Mount_M01.jpg"],["chaos-sorcerer-lord","Chaos Sorcerer Lord","Chaos_Sorcerer_Lord_02.jpeg"],["chaos-warrior","Chaos Warrior","Slaves_to_Darkness_vs_Daughters_of_Khaine_01.jpg"],["chaos-warshrine","Chaos Warshrine","Chaos_Warshrine_M01.jpg"],["exalted-hero-of-chaos","Exalted Hero of Chaos","Exalted_Hero_of_Chaos_M02.jpg"],["revenant-draconith","Revenant Draconith","Revenant_Draconith_M01.jpg"],["terrorgheist","Terrorgheist","Terrorgheist_01.png"],["zombie-dragon","Zombie Dragon","Zombie_Dragon_M01.jpg"],["corpse-cart","Corpse Cart","Corpse_Cart_01.jpg"],["dire-wolf","Dire Wolf","Dire_Wolves_01.jpg"],["kosargi-nightguard","Kosargi Nightguard","Kosargi_Nightguard_01.png"],["deadwalker-zombie","Zombie","Necromancer_and_Zombies_01.jpg"],["morghast-archai","Morghast Archai","Deathrattle_and_Morghast_01.jpg"],["morghast-harbinger","Morghast Harbinger","Morghast_C7.jpg"],["mortis-engine","Mortis Engine","Mortis_Engine_M01.jpg"],["necromancer","Necromancer","Necromancer_01.jpeg"],["barrow-knight","Barrow Knight","Black_Knight_C7.jpg"],["barrow-guard","Barrow Guard","Grave_Guard_C7.jpg"],["skeleton-warrior","Deathrattle Skeleton","Deathrattle_Army_01.jpg"],["wight-king","Wight King","Wight_King_on_Steed_01.jpeg"],["wight-lord","Wight Lord","Wight_Lord_on_Skeletal_Steed_M01.jpg"],["abhorrant-archregent","Abhorrant Archregent","Abhorrant_Archregent_01.jpg"],["abhorrant-cardinal","Abhorrant Cardinal","Abhorrant_Cardinal_profile_01.jpg"],["abhorrant-ghoul-king","Abhorrant Ghoul King","Pict_Abhorrant_Ghoul_King.jpg"],["abhorrant-gorewarden","Abhorrant Gorewarden","Abhorrant_Gorewarden_01.png"],["crypt-flayer","Crypt Flayer","Crypt_Flayer_M01.jpg"],["crypt-ghast-courtier","Crypt Ghast Courtier","Crypt_Ghast_Courtier_01.jpg"],["crypt-ghoul","Crypt Ghoul","Crypt_Ghouls_02.jpg"],["cryptguard","Cryptguard","Abhorrant_Gorewarden_01.png"],["crypt-haunter-courtier","Crypt Haunter Courtier","Crypt_Haunter_Courtier_01.jpg"],["crypt-horror","Crypt Horror","Crypt_Haunter_Courtier_02.jpg"],["crypt-infernal-courtier","Crypt Infernal Courtier","Crypt_Inferal_Courtier_01.jpg"],["marrowscroll-herald","Marrowscroll Herald","Marrowscroll_Herald_01.jpg"],["morbheg-knight","Morbheg Knight","Morbheg_Knights_M01.jpg"],["royal-beastflayers","Royal Beastflayers","Royal_Beastflayers_vs_Questor_Soulsworn_01.jpg"],["royal-decapitator","Royal Decapitator","Royal_Decapitator_M01.jpg"],["varghulf-courtier","Varghulf Courtier","Pict_Varghulf.jpg"],["black-coach","Black Coach","Black_Coach_01.jpg"],["bladegheist-revenant","Bladegheist Revenant","Slaves_to_Darkness_vs_Nighthaunt_01.jpg"],["cairn-wraith","Cairn Wraith","Cairn_Wraith_01.jpg"],["chainghast","Chainghast","Chainghast_M02.jpg"],["chainrasp","Chainrasp","Nighthaunt_02.jpeg"],["craventhrone-guard","Craventhrone Guard","Craventhrone_Guard_M01.jpg"],["dreadblade-harrow","Dreadblade Harrow","Nighthaunt_Procession_01.jpeg"],["dreadscythe-harridan","Dreadscythe Harridan","Dreadscythe_Harridan_01.jpg"],["glaivewraith-stalker","Glaivewraith Stalker","Glaivewraith_Stalkers_01.jpeg"],["grimghast-reaper","Grimghast Reaper","Grimghast_Reaper_01.jpeg"],["guardian-of-souls","Guardian of Souls","Guardian_of_Souls_02.jpg"],["hexwraith","Hexwraith","Hexwraiths_vs_Stormcast_01.jpeg"],["knight-of-shrouds","Knight of Shrouds","Knight_of_Shrouds_01.jpeg"],["krulghast-cruciator","Krulghast Cruciator","Krulghast_Cruciator_01.jpg"],["legion-black-coach","Legion Black Coach","Black_Coach_01.jpg"],["lord-executioner","Lord Executioner","Lord_Executioner_01.jpeg"],["lord-vitriolic","Lord Vitriolic","Lord_Vitriolic_M01.jpg"],["myrmourn-banshee","Myrmourn Banshee","Myrmourn_Banshee_C7.jpg"],["pyregheist","Pyregheist","Pyre_and_Flood_01.jpeg"],["scriptor-mortis","Scriptor Mortis","Scriptor_Mortis_01.jpg"],["spirit-host","Spirit Host","Pict_Spirit_Host.png"],["spirit-torment","Spirit Torment","Spirit_Torment_02.jpg"],["tomb-banshee","Tomb Banshee","Tomb_Banshee_M01.jpeg"],["gothizzar-harvester","Gothizzar Harvester","Gothizzar_Harvester_01.jpeg"],["immortis-guard","Immortis Guard","Immortis_Guard_01.jpeg"],["kavalos-deathrider","Kavalos Deathrider","Kavalos_Deathriders_01.jpeg"],["liege-kavalos","Liege-Kavalos","Liege-Kavalos_01.png"],["liege-mortek","Liege-Mortek","Liege-Mortek_M01.jpg"],["mortek-crawler","Mortek Crawler","Mortek_Crawler_M01.jpg"],["mortek-guard","Mortek Guard","Ossiarch_Army_01.jpeg"],["mortis-reaper","Mortis Reaper","Mortis_Reaper_M01.jpg"],["mortisan-boneshaper","Mortisan Boneshaper","Mortisan_C7.jpg"],["mortisan-ossifector","Mortisan Ossifector","Ossiarch_army_02.jpg"],["mortisan-soulmason","Mortisan Soulmason","Mortisan_Soulmason_M01.jpg"],["mortisan-soulreaper","Mortisan Soulreaper","Mortisan_Soulreaper_M01.jpg"],["necropolis-stalker","Necropolis Stalker","Necropolis_Stalker_C7.jpg"],["teratic-cohort","Teratic Cohort","Teratic_Cohort_01.jpg"],["askurgan-trueblades","Askurgan Trueblades","Askurgan_Trueblades_vs_Hounds_of_Karanak_01.jpg"],["bat-swarm","Bat Swarm","Bat_Swarm_M01.jpg"],["blood-knight","Blood Knight","Blood_Knight_vs_Marauder_01.jpeg"],["bloodseeker-palanquin","Bloodseeker Palanquin","Bloodseeker_Palanquin_M01.jpg"],["coven-throne","Coven Throne","Coven_Throne_M01.jpg"],["fell-bat","Fell Bat","Fell_Bat_M02.jpg"],["vampire-lord","Vampire Lord","Vampire_Lord_C7.jpg"],["vargheist","Vargheist","Vargheist.jpg"],["vargskyr","Vargskyr","Vargskyr_01.png"],["vengorian-lord","Vengorian Lord","Vengorian_Lord_M01.jpg"],["vyrkos-blood-born","Vyrkos Blood-born","Vyrkos_Blood-born_01.png"],["grot-scuttling","Grot Scuttling","Grot_Scuttling_M01.jpg"],["aleguzzler-gargant","Aleguzzler Gargant","Aleguzzler_Gargant_01.png"],["frost-sabre","Frost Sabre","Frost_Saber_Sketch_01.png"],["frostlord","Frostlord","Frostlord_on_Thundertusk_01.png"],["huskard","Huskard","Beastclaw_01.jpeg"],["icebrow-hunter","Icebrow Hunter","Pict_Ogor.png"],["icefall-yhetee","Icefall Yhetee","Pict_Icefall_Yhetee.jpg"],["mournfang-pack","Mournfang Pack","Mournfang_Pack_M01.jpg"],["stonehorn","Stonehorn","Pict_Stonehorn.jpg"],["thundertusk","Thundertusk","Pict_Thundertusk_2.png"],["maniak-weirdnob","Maniak Weirdnob","Maniak_Weirdnob_vs_Auric_Hearthguard_01.jpg"],["savage-big-stabba","Savage Big Stabba","Savage_Big_Stabba_vs_Mutalith_Vortex_Beast_01.jpg"],["savage-boarboy","Savage Boarboy","Savage_Boarboy_01.jpg"],["savage-boarboy-maniak","Savage Boarboy Maniak","Savage_Boarboy_Maniak_01.jpg"],["savage-orruk","Savage Orruk","Savage_Orruk_01.jpg"],["savage-orruk-arrowboy","Savage Orruk Arrowboy","Savage_Orruk_Arrowboy_01.jpg"],["savage-orruk-morboy","Savage Orruk Morboy","Pict_Orruk.jpg"],["wardokk","Wardokk","Wardokk_01.jpg"],["wurrgog-prophet","Wurrgog Prophet","Wurrgog_Prophet_01.jpg"],["savage-big-boss","Savage Big Boss","Bonesplitterz_vs_Seraphon_01.jpg"],["firebelly","Firebelly","Firebelly_M01.jpg"],["bloodpelt-hunter","Bloodpelt Hunter","Bloodpelt_Hunter_M01.jpg"],["butcher","Butcher","Butcher_01.png"],["glutton","Glutton","Glutton_M01.jpg"],["gorger","Gorger","Gorgers_vs_Wildercorps_Hunters_01.png"],["gorger-mawpack","Gorger Mawpack","Gorger_Face_&_Quote_01.png"],["gnoblar","Gnoblar","Ogors_and_Gnoblars_01.png"],["gnoblar-scraplauncher","Gnoblar Scraplauncher","Scraplauncher_M01.jpg"],["ironblaster","Ironblaster","Ironblaster_M01.jpg"],["irongut","Irongut","Irongut_M01.jpeg"],["leadbelcher","Leadbelcher","Leadbelcher_M01.jpg"],["slaughtermaster","Slaughtermaster","Slaughtermaster_M01.jpg"],["tyrant","Tyrant","Tyrant_M01.jpg"],["ardboy","Ardboy","Ardboys_M01.jpg"],["ardboy-big-boss","Ardboy Big Boss","Ardboy_Big_Boss_M01.jpg"],["brute","Brute","Brute_M01.jpg"],["brute-rager","Brute Rager","Brute_Ragerz_M01.jpg"],["gore-grunta","Gore-Grunta","Gore-Grunta_M01.jpg"],["maw-grunta-gouger","Maw-Grunta Gouger","Maw-Grunta_Gouger_M01.jpg"],["maw-grunta-with-hakkin%27-krew","Maw-Grunta with Hakkin\' Krew","Maw-Grunta_with_Hakkin\'_Krew_M01.jpg"],["megaboss","Megaboss","Megaboss_on_Maw-Krusha_M01.jpg"],["tuskboss","Tuskboss","Tuskboss_on_Maw_Grunta_M01.jpg"],["warchanter","Warchanter","Warchanter_M01.jpg"],["weirdbrute-wrekka","Weirdbrute Wrekka","Weirdbrute_Wrekkaz_M01.jpg"],["weirdnob-shaman","Weirdnob Shaman","Weirdnob_Shaman_M01.jpg"],["maneater","Maneater","Maneater_M01.jpg"],["boingrot-bounder","Boingrot Bounder","Boingrot_Bounder_M01.jpg"],["gobbapalooza#boggleye","Boggleye","Boggleye_M01.jpg"],["gobbapalooza#brewgit","Brewgit","Brewgit_M01.jpg"],["fungoid-cave-shaman","Fungoid Cave-Shaman","Fungoid_Cave-Shaman_M01.jpg"],["loonboss","Loonboss","Loonboss_on_Mangler_Squigs_M01.jpg"],["loonsmasha-fanatic","Loonsmasha Fanatic","Loonsmasha_Fanatic_M01.jpg"],["madcap-shaman","Madcap Shaman","Night_Goblin_Shaman_M02.jpg"],["mangler-squigs","Mangler Squigs","Mangler_Squig_M03.jpg"],["rabble-rowza","Rabble-Rowza","Rabble-Rowza_M01.jpg"],["gobbapalooza#scaremonger","Scaremonger","Scaremonger_M01.jpg"],["shoota","Shoota","Shoota_M01.jpg"],["gobbapalooza#shroomancer","Shroomancer","Shroomancer_M01.jpg"],["sneaky-snuffler","Sneaky Snuffler","Sneaky_Snuffler_M01.jpg"],["gobbapalooza#spiker","Spiker","Spiker_M01.jpg"],["sporesplatta-fanatic","Sporesplatta Fanatic","Sporesplatta_Fanatic_M01.jpg"],["squigboss","Squigboss","Squigboss_M01.jpg"],["squig-herd","Squig Herd","Squig_Herd_M01.jpg"],["squig-hopper","Squig Hopper","Squig_Hopper_M01.jpg"],["stabba","Stabba","Stabba_M01.jpg"],["doom-diver-catapult","Doom Diver Catapult","Doom_Diver_Catapult_M02.jpg"],["frazzlegit-shaman","Frazzlegit Shaman","Frazzlegit_Shaman_On_War-Wheela_M01.jpg"],["snarlboss","Snarlboss","Snarlboss_On_War-Wheela_M01.jpg"],["snarlfang-rider","Snarlfang Rider","Snarlfang_Riders_M01.jpg"],["snarlpack-cavalry","Snarlpack Cavalry","Snarlpack_Cavalry_M01.jpg"],["sunsteala-wheela","Sunsteala Wheela","Sunsteala_Wheelas_M01.jpg"],["arachnarok-spider","Arachnarok Spider","Arachnarok_Spider_with_Spiderfang_Warparty_M01.jpg"],["scuttleboss","Scuttleboss","Scuttleboss_on_Gigantic_Spider_M01.jpeg"],["skitterstrand-arachnarok","Skitterstrand Arachnarok","SkitterstrandArachnarok.jpg"],["spider-rider","Spider Rider","Spider_Rider_M02.jpg"],["webspinner-shaman","Webspinner Shaman","Webspinner_Shaman_on_Arachnarok_Spider_M01.jpg"],["dankhold-troggboss","Dankhold Troggboss","Dankhold_Troggboss_M01.jpg"],["dankhold-troggoth","Dankhold Troggoth","Dankhold_Troggoth_M01.jpg"],["fellwater-troggoth","Fellwater Troggoth","Fellwater_Troggoth_M02.jpg"],["rockgut-troggoth","Rockgut Troggoth","Rockgut_Troggoth_M01.jpg"],["mistweaver-saih","Mistweaver Saih","Mistweaver_Saih_M01.jpg"],["tenebrael-shard","Tenebrael Shard","Tenebrael_Shard_M01.jpg"],["alchemite-warforger","Alchemite Warforger","Alchemite_Warforger_M01.jpg"],["amethyst-knellmage","Amethyst Knellmage","Amethyst_Knellmage_M01.jpg"],["aqshian-pyrocaster","Aqshian Pyrocaster","Aqshian_Pyrocaster_M01.jpg"],["battlemage","Battlemage","Battlemage_on_Griffon_M01.jpeg"],["celestial-hurricanum","Celestial Hurricanum","Celestial_Hurricanum_M01.jpg"],["luminark-of-hysh","Luminark of Hysh","Luminark_M01.jpeg"],["black-guard","Black Guard","Black_Guard_M01.jpg"],["bleaksword","Bleaksword","Bleaksword_M01.jpg"],["darkshard","Darkshard","Darkshard_M01.jpg"],["dreadspear","Dreadspear","Dreadspear_M01.jpg"],["executioner","Executioner","Executioner_M01.jpg"],["sorceress","Sorceress","Sorceress_on_Black_Dragon_M01.jpg"],["avatar-of-khaine","Avatar of Khaine","Avatar_of_Khaine_M01.jpg"],["bloodwrack-medusa","Bloodwrack Medusa","Bloodwrack_Medusa_M01.jpg"],["bloodwrack-shrine","Bloodwrack Shrine","Bloodwrack_Shrine_M01.jpg"],["blood-sister","Blood Sister","Melusai_Blood_Sister_M01.jpg"],["blood-stalker","Blood Stalker","Melusai_Blood_Stalker_M01.jpg"],["melusai-ironscale","Melusai Ironscale","Melusai_Ironscale_M01.jpg"],["doomfire-warlock","Doomfire Warlock","Doomfire_Warlock_M01.jpg"],["hag-queen","Hag Queen","Hag_Queen_on_Cauldron_of_Blood_M01.jpg"],["high-gladiatrix","High Gladiatrix","High_Gladiatrix_M01.jpg"],["khainite-shadowstalkers","Khainite Shadowstalkers","Khainite_Shadowstalkers_M01.jpg"],["khinerai-heartrender","Khinerai Heartrender","Khinerai_Heartrender_M01.jpg"],["khinerai-lifetaker","Khinerai Lifetaker","Khinerai_Lifetaker_M01.jpg"],["sister-of-slaughter","Sister of Slaughter","Sister_of_Slaughter_M01.jpg"],["slaughter-queen","Slaughter Queen","Slaughter_Queen_on_Cauldron_of_Blood_M01.jpg"],["witch-aelf","Witch Aelf","Witch_Aelf_M01.jpg"],["flagellant","Flagellant","Flagellant_M01.jpeg"],["mallus-forgepriest","Mallus Forgepriest","Mallus_Forgepriest_M01.jpg"],["hammerer","Hammerer","Hammerer_M01.jpg"],["ironbreaker","Ironbreaker","Ironbreaker_M01.jpg"],["irondrake","Irondrake","Irondrake_M01.jpg"],["longbeard","Longbeard","Longbeard_M01.jpg"],["runelord","Runelord","Runelord_M01.jpg"],["warden-king","Warden King","Warden_King_M01.jpg"],["freeguild-cavalier","Freeguild Cavalier","Freeguild_Cavalier_M01.jpg"],["freeguild-cavalier-marshal","Freeguild Cavalier-Marshal","Freeguild_Cavalier-Marshal_M01.jpg"],["freeguild-command-corps","Freeguild Command Corps","Freeguild_Command_Corps_M01.jpg"],["freeguild-fusilier","Freeguild Fusilier","Freeguild_Fusiliers_M01.jpg"],["freeguild-gallant","Freeguild Gallant","Freeguild_Gallant_M01.jpg"],["freeguild-general","Freeguild General","Freeguild_General_on_Griffon_M01.jpg"],["freeguild-grenadier","Freeguild Grenadier","Freeguild_Grenadier_M01.jpg"],["freeguild-marshal","Freeguild Marshal","Freeguild_Marshal_and_Relic_Envoy_M01.jpg"],["freeguild-steelhelm","Freeguild Steelhelm","Freeguild_Steelhelms_M01.jpg"],["fusil-major","Fusil-Major","Fusil-Major_on_Ogor_Warhulk_M01.jpg"],["gate-gargant","Gate Gargant","Gate_Gargants_M01.jpg"],["wildercorps-hunter","Wildercorps Hunter","Wildercorps_Hunters_M01.jpg"],["auric-flamekeeper","Auric Flamekeeper","Auric_Flamekeeper_M01.jpg"],["auric-hearthguard","Auric Hearthguard","Auric_Hearthguard_M01.jpg"],["auric-runefather","Auric Runefather","Auric_Runefather_on_Magmadroth_M01.jpg"],["auric-runemaster","Auric Runemaster","Auric_Runemaster_M01.jpg"],["auric-runesmiter","Auric Runesmiter","Auric_Runesmiter_on_Magmadroth_M01.jpg"],["auric-runeson","Auric Runeson","Auric_Runeson_on_Magmadroth_M02.jpg"],["battlesmith","Battlesmith","Battlesmith_M01.jpg"],["fyreslayer-doomseeker","Fyreslayer Doomseeker","Doomseeker_M01.jpg"],["grimhold-exile","Grimhold Exile","Grimhold_Exile_M01.jpg"],["grimwrath-berzerker","Grimwrath Berzerker","Grimwrath_Berzerker_M01.jpg"],["hearthguard-berzerker","Hearthguard Berzerker","Hearthguard_Berzerker_M01.jpg"],["vulkite-berzerker","Vulkite Berzerker","Vulkite_Berzerker_M01.jpg"],["vulkyn-flameseeker","Vulkyn Flameseeker","Vulkyn_Flameseekers_M01.jpg"],["akhelian-allopex","Akhelian Allopex","Akhelian_Allopex_M01.jpg"],["akhelian-guard","Akhelian Morrsarr Guard","Akhelian_Morrsarr_Guard_M01.jpg"],["akhelian-king","Akhelian King","Akhelian_King_M01.jpg"],["akhelian-leviadon","Akhelian Leviadon","Akhelian_Leviadon_M01.jpg"],["akhelian-thrallmaster","Akhelian Thrallmaster","Akhelian_Thrallmaster_M01.jpg"],["eidolon-of-mathlann","Eidolon of Mathlann","Eidolon_of_Mathlann_M02.jpg"],["ikon","Ikon","Ikon_Of_The_Storm_M01.jpg"],["soulrender","Isharaan Soulrender","Isharann_Soulrender_M01.jpg"],["soulscryrer","Isharann Soulscryer","Isharann_Soulscryer_M01.jpg"],["tidecaster","Isharann Tidecaster","Isharann_Tidecaster_M01.jpg"],["namarti-thrall","Namarti Thrall","Namarti_Thrall_M01.jpg"],["namarti-reaver","Namarti Reaver","Namarti_Reaver_M01.jpg"],["cannonade-cogfort","Cannonade Cogfort","Cannonade_Cogfort_M01.jpg"],["conqueror-cogfort","Conqueror Cogfort","Conqueror_Cogfort_M01.jpg"],["cogsmith","Cogsmith","Cogsmith_M01.jpg"],["gyrobomber","Gyrobomber","Gyrobomber_M01.jpg"],["gyrocopter","Gyrocopter","Gyrocopter_M01.jpg"],["ironweld-great-cannon","Ironweld Great Cannon","Ironweld_Great_Cannon_M01.jpg"],["steam-tank","Steam Tank","Steam_Tank_M01.jpg"],["aether-khemist","Aether-Khemist","Aether-Khemist_M01.jpg"],["aetheric-navigator","Aetheric Navigator","Aetheric_Navigator_M01.jpg"],["arkanaut-admiral","Arkanaut Admiral","Arkanaut_Admiral_M01.jpg"],["arkanaut-company","Arkanaut Company","Arkanaut_Company_M01.jpg"],["arkanaut-frigate","Arkanaut Frigate","Arkanaut_Frigate_M01.jpg"],["arkanaut-ironclad","Arkanaut Ironclad","Arkanaut_Ironclad_M01.jpg"],["codewright","Codewright","Codewright_M01.jpg"],["endrinmaster","Endrinmaster","Endrinmaster_M02.jpg"],["endrinrigger","Endrinrigger","Endrinrigger_M01.jpg"],["grundstok-gunhauler","Grundstok Gunhauler","Grundstok_Gunhauler_M01.jpg"],["grundstok-thunderer","Grundstok Thunderer","Grundstok_Thunderer_M01.jpg"],["null-khemist","Null-Khemist","Null-Khemist_M01.jpg"],["skywarden","Skywarden","Skywarden_M01.jpg"],["vongrim-salvager","Vongrim Salvager","Unknown_M01.png"],["white-lion","White Lion","White_Lion_M01.jpeg"],["white-lion-chariot","White Lion Chariot","White_Lion_Chariot_M01.jpg"],["drakespawn-chariot","Drakespawn Chariot","Drakespawn_Chariot_M01.jpg"],["drakespawn-knight","Drakespawn Knight","Drakespawn_Knight_M01.jpg"],["dreadlord","Dreadlord","Dreadlord_on_Black_Dragon_M01.jpg"],["war-hydra","War Hydra","War_Hydra_M02.jpg"],["black-ark-corsair","Black Ark Corsair","Black_Ark_Corsair_M01.jpg"],["black-ark-fleetmaster","Black Ark Fleetmaster","Black_Ark_Fleetmaster_M01.jpg"],["kharibdyss","Kharibdyss","Kharibdyss_M01.jpg"],["scourgerunner-chariot","Scourgerunner Chariot","Scourgerunner_Chariot_M01.jpg"],["aggradon-lancer","Aggradon Lancer","Aggradon_Lancers_M01.jpg"],["bastiladon","Bastiladon","Bastiladon_M01.jpg"],["chameleon-skink","Chameleon Skink","Chameleon_Skink_M01.jpg"],["hunters-of-huanchi","Hunters of Huanchi","Hunters_of_Huanchi_M01.jpg"],["engine-of-the-gods","Engine of the Gods","Engine_of_the_Gods_M01.jpg"],["kroxigor","Kroxigor","Kroxigor_M05.jpg"],["kroxigor-warspawned","Kroxigor Warspawned","Kroxigor_Warspawned_M01.jpg"],["raptadon-charger","Raptadon Charger","Raptadon_Chargers_M01.jpg"],["raptadon-hunter","Raptadon Hunter","Raptadon_Hunters_M01.jpg"],["razordon","Razordon","Razordon_M01.jpg"],["ripperdactyl-chief","Ripperdactyl Chief","Ripperdactyl_Rider_M04.jpg"],["ripperdactyl-rider","Ripperdactyl Rider","Ripperdactyl_Rider_M01.jpg"],["salamander","Salamander","Salamander_M01.jpg"],["saurus-astrolith-bearer","Saurus Astrolith Bearer","Saurus_Astrolith_Bearer_M03.jpg"],["saurus-eternity-warden","Saurus Eternity Warden","Saurus_Eternity_Warden_M01.jpg"],["saurus-guard","Saurus Guard","Saurus_Guard_M01.jpg"],["saurus-knight","Saurus Knight","Saurus_Knight_M01.jpg"],["saurus-oldblood","Saurus Oldblood","Saurus_Oldblood_on_Carnosaur_M01.jpg"],["saurus-scar-veteran","Saurus Scar-Veteran","Saurus_Scar-Veteran_on_Cold_One_M01.jpg"],["saurus-sunblood","Saurus Sunblood","Saurus_Sunblood_M01.jpg"],["saurus-warrior","Saurus Warrior","Saurus_Warrior_M05.jpg"],["skink-skirmisher","Skink","Skink_M01.jpg"],["skink-handler","Skink Handler","Skink_Handler_M02.jpg"],["skink-priest","Skink Priest","Skink_Priest_M01.jpg"],["skink-starpriest","Skink Starpriest","Skink_Starpriest_M01.jpg"],["skink-starseer","Skink Starseer","Skink_Starseer_M03.jpg"],["slann-starmaster","Slann Starmaster","Slann_Starmaster_M03.jpg"],["spawn-of-chotec","Spawn of Chotec","Spawn_of_Chotec_M01.jpg"],["stegadon","Stegadon","Stegadon_M02.jpg"],["terradon-chief","Terradon Chief","Terradon_Rider_M03.jpg"],["terradon-rider","Terradon Rider","Terradon_Rider_M01.jpg"],["skink-oracle","Skink Oracle","Troglodon_M02.jpg"],["assassin","Assassin","Assassin_M01.jpg"],["dark-rider","Dark Rider","Dark_Rider_M01.jpg"],["aetherwing","Aetherwing","Aetherwing_M01.jpg"],["annihilator","Annihilator","Annihilator_M01.jpg"],["castigator","Castigator","Castigator_M01.jpg"],["celestar-ballista","Celestar Ballista","Celestar_Ballista_M01.jpg"],["concussor","Concussor","Concussor_M01.jpg"],["decimators","Decimators","Decimator_M01.jpg"],["desolator","Desolator","Desolator_M01.jpg"],["drakesworn-templar","Drakesworn Templar","Drakesworn_Templar_M01.jpg"],["evocator","Evocator","Evocator_on_Dracoline_M01.jpg"],["fulminator","Fulminator","Fulminator_M01.jpg"],["gryph-hound","Gryph-Hound","Gryph-Hound_M01.jpg"],["judicator","Judicator","Judicator_M01.jpg"],["knight-arcanum","Knight-Arcanum","Knight_Arcanum_M01.jpg"],["knight-azyros","Knight-Azyros","Knight-Azyros_M01.jpg"],["knight-draconis","Knight-Draconis","Knight-Draconis_M01.jpg"],["knight-heraldor","Knight-Heraldor","Knight-Heraldor_M01.jpg"],["knight-incantor","Knight-Incantor","Knight-Incantor_M01.jpg"],["knight-judicator","Knight-Judicator","Knight-Judicator_M01.jpg"],["knight-questor","Knight-Questor","Knight-Questor_M03.jpg"],["knight-relictor","Knight-Relictor","Knight-Relictor_M01.jpg"],["knight-venator","Knight-Venator","Knight-Venator_M01.jpg"],["knight-vexillor","Knight-Vexillor","Knight-Vexillor_M01.jpg"],["liberator","Liberator","Liberator_M12.jpg"],["lord-aquilor","Lord-Aquilor","Lord-Aquilor_M01.jpg"],["lord-arcanum","Lord-Arcanum","Lord-Arcanum_on_Tauralon_M01.jpg"],["lord-castellant","Lord-Castellant","Lord-Castellant_M01.jpg"],["lord-celestant","Lord-Celestant","Lord-Celestant_on_Stardrake_M01.jpg"],["lord-exorcist","Lord-Exorcist","Lord-Exorcist_M01.jpg"],["lord-imperatant","Lord-Imperatant","Lord-Imperatant_M01.jpg"],["lord-ordinator","Lord-Ordinator","Lord-Ordinator_M01.jpg"],["lord-relictor","Lord-Relictor","Lord-Relictor_M03.jpg"],["lord-terminos","Lord-Terminos","Lord-Terminos_M01.jpg"],["lord-vigilant","Lord-Vigilant","Lord_Vigilant_on_Morrgyph_M01.jpg"],["lord-veritant","Lord-Veritant","Lord-Veritant_M04.jpg"],["praetor","Praetor","Praetor_M01.jpg"],["prosecutor","Prosecutor","Prosecutor_M10.jpg"],["protector","Protector","Protector_M01.jpg"],["questor-soulsworn","Questor Soulsworn","Questor_Soulsworn_M01.jpg"],["reclusian","Reclusian","Reclusian_M01.jpg"],["retributor","Retributor","Retributor_M01.jpg"],["sequitor","Sequitor","Sequitor_M01.jpg"],["stormdrake-guard","Stormdrake Guard","Stormdrake-Guard_M01.jpg"],["stormstrike-chariot","Stormstrike Chariot","Stormstrike_Chariot_M01.jpg"],["stormstrike-pallador","Stormstrike Pallador","Stormstrike_Pallador_M01.jpg"],["tempestor","Tempestor","Tempestor_M01.jpg"],["vanguard-hunter","Vanguard-Hunter","Vanguard-Hunter_M01.jpg"],["vanguard-pallador","Vanguard-Pallador","Vanguard-Pallador_M01.jpg"],["vanguard-raptor","Vanguard-Raptor","Vanguard-Raptor_M01.jpg"],["vanquisher","Vanquisher","Vanquisher_M01.jpg"],["vigilor","Vigilor","Vigilor_M01.jpg"],["vindictor","Vindictor","Vindictors_M01.jpg"],["arch-revenant","Arch-Revenant","Arch-Revenant_M01.jpg"],["branchwraith","Branchwraith","Branchwraith_M01.jpg"],["branchwych","Branchwych","Branchwych_M01.jpg"],["dryad","Dryad","Dryad_M01.jpg"],["gossamid-archers","Gossamid Archers","Gossamid_Archers_M01.jpg"],["kurnoth-hunter","Kurnoth Hunter","Kurnoth_Hunter_M01.jpg"],["revenant-seekers","Revenant Seekers","Revenant_Seekers_M01.jpg"],["spirit-of-durthu","Spirit of Durthu","Spirit_of_Durthu_M01.jpg"],["spiterider-lancers","Spiterider Lancers","Spiterider_Lancers_M01.jpg"],["spite-revenant","Spite-Revenant","Spite-Revenant_M01.jpg"],["tree-revenant","Tree-Revenant","Tree-Revenant_M01.jpg"],["treelord","Treelord","Treelord_M01.jpg"],["treelord-ancient","Treelord Ancient","Treelord_Ancient_M01.jpg"],["twistweald","Twistweald","Twistweald_M01.jpg"],["warsong-revenant","Warsong Revenant","Warsong_Revenant_M01.jpg"],["brayherds","Brayherds","Gor_01.jpg"],["beasts-of-chaos","Beasts Of Chaos",""],["grand-alliance-of-chaos","Grand Alliance Of Chaos","Realm_of_Chaos_01.png"],["daemons-of-chaos","Daemons Of Chaos","Be\'lakor_02.jpg"],["slaves-to-darkness","Slaves To Darkness","Lord_Infernil\'s_Reavers.jpg"],["chaos-familiar","Chaos Familiar","Mibyllorr_and_Familiars_M01.jpg"],["disc-of-tzeentch","Disc Of Tzeentch","Pict_Disc_of_Tzeentch.jpg"],["daemons-of-khorne","Daemons Of Khorne","Bloodletter_01.jpg"],["blades-of-khorne","Blades Of Khorne","Khornate_Stronghold_01.png"],["daemons-of-nurgle","Daemons Of Nurgle","Daemons_of_Nurgle_03.jpg"],["maggotkin-of-nurgle","Maggotkin Of Nurgle","Drowned_Men_Icon.jpg"],["herald-of-nurgle","Herald Of Nurgle","Poxbringer_M01.jpg"],["daemons-of-tzeentch","Daemons Of Tzeentch","Daemons_of_Tzeentch_01.png"],["disciples-of-tzeentch","Disciples Of Tzeentch","Arcanite_chart_01.png"],["burning-chariot","Burning Chariot","Herald_of_Tzeentch_03.jpg"],["daemons-of-slaanesh","Daemons Of Slaanesh","Daemonette_04.jpeg"],["hedonites-of-slaanesh","Hedonites Of Slaanesh",""],["seeker-chariot","Seeker Chariot","Seeker_Chariot_01.jpg"],["eshin","Eshin","Gutter_Runner_01.png"],["skaventide","Skaventide",""],["everchosen","Everchosen","Archaon_leading_the_Varanguard_01.jpeg"],["slaanesh-sybarites","Slaanesh Sybarites","Slaanesh_Sybarites_01.jpg"],["khorne-bloodbound","Khorne Bloodbound","Goretide_01.png"],["masterclan","Masterclan","Skaven_01.jpeg"],["monsters-of-chaos","Monsters Of Chaos","Chimera_02.png"],["moulder","Moulder","Clan_Moulder_01.png"],["nurgle-rotbringers","Nurgle Rotbringers","Maggotkin_of_Nurgle_02.jpeg"],["pestilens","Pestilens","Pict_Skaven.png"],["skryre","Skryre","Skryre_01.png"],["thunderscorn","Thunderscorn","Dragon_Ogor_01.jpeg"],["tzeentch-arcanites","Tzeentch Arcanites","Order_vs_Tzeentch_Arcanites_01.jpeg"],["tzeentch-sorcerer-lord","Tzeentch Sorcerer Lord","Chaos_Sorcerer_Lord_02.jpeg"],["verminus","Verminus","Verminus_01.png"],["warherds","Warherds","Cygor_01.jpg"],["daemonic-mount","Daemonic Mount","Daemonic_Mounts_01.jpg"],["karkadrak","Karkadrak","Chaos_Lord_on_Karkadrak_M01.jpg"],["manticore","Manticore",""],["beasts-of-the-grave","Beasts Of The Grave","Terrorgheist_01.png"],["grand-alliance-of-death","Grand Alliance Of Death","Soulblight_01.jpg"],["deadwalkers","Deadwalkers","Corpse_Cart_01.jpg"],["soulblight-gravelords","Soulblight Gravelords","Soulblight_Gravelords_Cover_Art_01.jpeg"],["deathlords","Deathlords","Nagash_and_Morghasts_01.jpg"],["ossiarch-bonereapers","Ossiarch Bonereapers","Ossiarch_Army_01.jpeg"],["deathmages","Deathmages","Mortis_Engine_01.jpg"],["deathrattle","Deathrattle","Wight_King_on_Steed_01.jpeg"],["skeletal-steed","Skeletal Steed","Wight_King_on_Skeletal_Steed_M01.jpg"],["flesh-eater-courts","Flesh Eater Courts","Abhorrant_Archregent_01.jpg"],["nighthaunt","Nighthaunt","Nighthaunt_01.jpg"],["ethereal-steed","Ethereal Steed","Knight_of_Shrouds_01.jpeg"],["soulblight","Soulblight","Bloodseeker_Palanquin_01.jpg"],["grand-alliance-of-destruction","Grand Alliance Of Destruction","Gloomspite_vs_Stormcast_02.jpeg"],["aleguzzler-gargants","Aleguzzler Gargants","Aleguzzler_Gargant_01.png"],["gloomspite-gitz","Gloomspite Gitz","Gloomspite_Gitz_01.jpeg"],["beastclaw-raiders","Beastclaw Raiders","Beastclaw_01.jpeg"],["ogor-mawtribes","Ogor Mawtribes","Ogor_Army_01.jpg"],["beastrider","Beastrider",""],["bonesplitterz","Bonesplitterz","Bonesplitterz_02.jpeg"],["orruk-warclans","Orruk Warclans","Orruk_Warclans_01.jpeg"],["firebellies","Firebellies","Firebellies_01.png"],["gutbusters","Gutbusters","Gutbusters_01.jpg"]]';
  const UNITS = JSON.parse(UNITS_JSON);

  // --------------------------------------------------------------- config
  const BASE         = "https://ageofsigmar.lexicanum.com";
  const GALLERY_PATH = "/wiki/Gallery:";
  const REQ_DELAY_MS = 250;
  const CHECKPOINT_EVERY = 100;
  const LOG_EVERY        = 10;

  // ----------------------------------------------------------- JSZip load
  async function loadJSZip() {
    if (typeof JSZip !== "undefined") return;
    await new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = "https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js";
      s.onload  = resolve;
      s.onerror = () => reject(new Error("Failed to load JSZip from CDN"));
      document.head.appendChild(s);
    });
  }

  // -------------------------------------------------------- helper utils
  const delay = ms => new Promise(r => setTimeout(r, ms));

  function extFromUrl(url) {
    const path = url.split("?")[0].split("#")[0];
    const m = path.match(/\.(jpe?g|png|gif|webp|svg)$/i);
    if (m) return m[1].toLowerCase().replace("jpeg", "jpg");
    return "jpg";
  }

  // Decode and basename of a URL path component
  function basenameFromUrl(url) {
    try {
      const path = url.split("?")[0].split("#")[0];
      const last = path.substring(path.lastIndexOf("/") + 1);
      return decodeURIComponent(last);
    } catch (_) {
      return url.substring(url.lastIndexOf("/") + 1);
    }
  }

  // Convert MediaWiki thumb URL to its original/full file URL.
  // Thumb pattern:  /mediawiki/images/thumb/X/YY/File.jpg/NNNpx-File.jpg
  // Original:       /mediawiki/images/X/YY/File.jpg
  function thumbToFull(url) {
    if (!url) return url;
    // Resolve protocol-relative or absolute
    let abs;
    try { abs = new URL(url, BASE).toString(); }
    catch (_) { abs = url; }
    const re = /\/mediawiki\/images\/thumb\/([0-9a-f])\/([0-9a-f]{2})\/([^/]+)\/[^/]+$/i;
    return abs.replace(re, "/mediawiki/images/$1/$2/$3");
  }

  function triggerDownload(blob, filename) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      URL.revokeObjectURL(a.href);
      document.body.removeChild(a);
    }, 5000);
  }

  // ------------------------------------------------------- HTTP helpers
  async function fetchHTML(url) {
    let resp;
    try { resp = await fetch(url, { credentials: "include" }); }
    catch (e) { return { status: 0, html: null }; }
    if (!resp.ok) return { status: resp.status, html: null };
    const ct = resp.headers.get("content-type") || "";
    if (!ct.toLowerCase().includes("text/html")) {
      return { status: resp.status, html: null }; // CF challenge or otherwise
    }
    const html = await resp.text();
    return { status: resp.status, html };
  }

  async function fetchImageBlob(url) {
    let resp;
    try { resp = await fetch(url, { credentials: "include" }); }
    catch (e) { return null; }
    if (!resp.ok) return null;
    const ct = resp.headers.get("content-type") || "";
    if (!ct.startsWith("image/")) return null; // probably a CF challenge
    const buf = await resp.arrayBuffer();
    if (buf.byteLength < 1024) return null;
    return new Blob([buf], { type: ct });
  }

  // -------------------------------------------------- gallery extractor
  // Returns array of { url, basename } resolved to full-size mediawiki URLs,
  // de-duplicated, in source order.
  function extractGalleryImages(html) {
    const doc = new DOMParser().parseFromString(html, "text/html");
    const out  = [];
    const seen = new Set();

    // MediaWiki galleries: .gallery, .gallerybox, .mw-gallery-*
    const containers = doc.querySelectorAll(
      ".gallery, .gallerybox, .mw-gallery-traditional, .mw-gallery-packed, " +
      ".mw-gallery-nolines, .mw-gallery-slideshow"
    );

    const collect = (root) => {
      const links = root.querySelectorAll("a.image, a.mw-file-description");
      links.forEach(a => {
        const img = a.querySelector("img");
        if (!img) return;
        const src = img.getAttribute("src");
        if (!src) return;
        const full = thumbToFull(src);
        if (!full || seen.has(full)) return;
        seen.add(full);
        out.push({ url: full, basename: basenameFromUrl(full) });
      });
    };

    if (containers.length > 0) {
      containers.forEach(collect);
    }
    return out;
  }

  // ----------------------------------------------------------------- run
  await loadJSZip();
  console.log("[lex-gal] JSZip loaded. Processing", UNITS.length, "units.");

  let zip = new JSZip();
  const manifest = {}; // slug -> [{filename, source_url, was_filtered_warscroll}]
  const results = {
    ok: 0, no_gallery: 0, http_404: 0, http_other: 0, errors: 0,
    images_saved: 0, images_filtered_warscroll: 0
  };
  const total = UNITS.length;

  for (let i = 0; i < total; i++) {
    const entry = UNITS[i] || [];
    const slug  = entry[0];
    const title = entry[1];
    const warscrollFile = entry[2] || "";

    if (!slug || !title) {
      results.errors++;
      continue;
    }

    let savedThisUnit = 0;
    let filteredThisUnit = 0;
    let status404 = false;
    let httpStatus = 0;

    try {
      const galleryURL = BASE + GALLERY_PATH + encodeURIComponent(
        title.replace(/ /g, "_")
      );
      const { status, html } = await fetchHTML(galleryURL);
      httpStatus = status;

      if (status === 404) {
        status404 = true;
        results.http_404++;
      } else if (status !== 200 || !html) {
        results.http_other++;
      } else {
        const images = extractGalleryImages(html);
        if (images.length === 0) {
          results.no_gallery++;
        }
        let idx = 0;
        for (const img of images) {
          // Filter out the warscroll/infobox art so we don't duplicate it.
          const isWarscroll = !!warscrollFile && img.basename === warscrollFile;
          if (isWarscroll) {
            filteredThisUnit++;
            results.images_filtered_warscroll++;
            (manifest[slug] = manifest[slug] || []).push({
              filename: null,
              source_url: img.url,
              was_filtered_warscroll: true
            });
            continue;
          }

          await delay(REQ_DELAY_MS);
          const blob = await fetchImageBlob(img.url);
          if (!blob) continue;

          const ext = extFromUrl(img.url);
          const filename = `${slug}__${String(idx).padStart(2, "0")}.${ext}`;
          zip.file(filename, blob);
          (manifest[slug] = manifest[slug] || []).push({
            filename,
            source_url: img.url,
            was_filtered_warscroll: false
          });
          idx++;
          savedThisUnit++;
          results.images_saved++;
        }
        if (savedThisUnit > 0) results.ok++;
      }
    } catch (err) {
      results.errors++;
      console.warn("[lex-gal] error", slug, err);
    }

    // Progress log
    if ((i + 1) % LOG_EVERY === 0 || i === total - 1) {
      const tag = status404
        ? "404"
        : (httpStatus && httpStatus !== 200 ? `HTTP ${httpStatus}` : "");
      console.log(
        `[lex-gal] [${String(i + 1).padStart(3, "0")}/${total}] ${slug} — ` +
        `${savedThisUnit} images / ${filteredThisUnit} filtered` +
        (tag ? ` / ${tag}` : "")
      );
    }

    // Inter-unit polite delay
    await delay(REQ_DELAY_MS);

    // Checkpoint
    if ((i + 1) % CHECKPOINT_EVERY === 0) {
      const checkName =
        `lex_gallery_images_checkpoint_${String(i + 1).padStart(4, "0")}.zip`;
      console.log(`[lex-gal] CHECKPOINT -> ${checkName} ` +
                  `(saved=${results.images_saved})`);
      try {
        const cb = await zip.generateAsync({ type: "blob" });
        triggerDownload(cb, checkName);
      } catch (e) {
        console.warn("[lex-gal] checkpoint failed:", e);
      }
    }
  }

  // ------------------------------------------------------ final outputs
  console.log("[lex-gal] DONE", results);
  try {
    const finalZip = await zip.generateAsync({ type: "blob" });
    triggerDownload(finalZip, "lex_gallery_images.zip");
  } catch (e) {
    console.error("[lex-gal] final zip generation failed:", e);
  }

  const manifestBlob = new Blob(
    [JSON.stringify(
      { generated_at: new Date().toISOString(), stats: results, units: manifest },
      null, 2
    )],
    { type: "application/json" }
  );
  triggerDownload(manifestBlob, "lex_gallery_manifest.json");

  console.log("[lex-gal] All downloads queued.");
})();
