# Mission A: Copy 25 downloaded images to correct faction subdirs
# Downloads -> app/static/img/units/<faction>/<slug>.<ext>

$downloads = "C:\Users\eep0x10\Downloads"
$units_base = "C:\Users\eep0x10\dev\waaahgame\app\static\img\units"

# Mapping: source filename -> (faction_dir, target_slug)
# Based on the 25 files found and DB image_path info
$mappings = @(
    @{ src="99120209051_SkragrottLoonking01.jpg";          faction="gloomspite-gitz";          slug="skragrott-the-loonking" },
    @{ src="99120209043_MoonclanGrots01.jpg";              faction="gloomspite-gitz";          slug="moonclan-grots" },
    @{ src="99120205023_BrokkGrungsson01.jpg";             faction="kharadron-overlords";      slug="brokk-grungsson-lord-magnate-of-barak-nar" },
    @{ src="99120210039_LRLAvalenorStoneheartKingAlt.jpg"; faction="lumineth-realm-lords";     slug="alarith-spirit-of-the-mountain" },
    @{ src="99120210036_LRLAlarStoneguardLead.jpg";        faction="lumineth-realm-lords";     slug="alarith-stoneguard" },
    @{ src="99120210037_LRLAlaStonLead.jpg";               faction="lumineth-realm-lords";     slug="alarith-stonemage" },
    @{ src="99070210004_LRLScinariCathLead.jpg";           faction="lumineth-realm-lords";     slug="scinari-cathallar" },
    @{ src="99120210040_LightEltharionLead.jpg";           faction="lumineth-realm-lords";     slug="the-light-of-eltharion" },
    @{ src="99120210031_LRLLyriorUthralleVanariLordRegentLeadAlt.jpg"; faction="lumineth-realm-lords"; slug="vanari-lord-regent" },
    @{ src="99120210042_VanAurWarLead.jpg";                faction="lumineth-realm-lords";     slug="vanari-auralan-wardens" },
    @{ src="99129915063_NURMoNRotigusLead.jpg";            faction="maggotkin-of-nurgle";      slug="rotigus" },
    @{ src="99120209032_GodrakkonBigTeef01.jpg";           faction="orruk-warclans";           slug="gordrakk-the-fist-of-gork" },
    @{ src="99120209124_OWSwampcallaShamanPotgrotCharacter1.jpg"; faction="orruk-warclans";    slug="swampcalla-shaman-with-pot-grot" },
    @{ src="99120209077_GutrippazLead.jpg";                faction="orruk-warclans";           slug="kruleboyz-gutrippaz" },
    @{ src="99120207029_DeathLordsNagashSupremelordoftheUndead01.jpg"; faction="ossiarch-bonereapers"; slug="nagash-supreme-lord-of-the-undead" },
    @{ src="99120206059_SKAThanqoulOnBoneripper01.jpg";    faction="skaven";                   slug="thanquol-on-boneripper" },
    @{ src="99120201045_ArchaonEverchosen01.jpg";          faction="slaves-to-darkness";       slug="archaon-the-everchosen" },
    @{ src="99129915058_ChaosDaemonsBelakortheDarkMasterLead.jpg"; faction="slaves-to-darkness"; slug="be-lakor-the-dark-master" },
    @{ src="99120207179_SoulblightGravelordsBarrowKnights1.jpg"; faction="soulblight-gravelords"; slug="barrow-knight" },
    @{ src="99120207031_DeathLordsMortarchsMannfred01.jpg"; faction="soulblight-gravelords";   slug="mannfred-von-carstein-mortarch-of-night" },
    @{ src="vampire-lord-on-zombie-dragon-ready-for-the-battle-v0-h6oxre7vs1ef1.webp"; faction="soulblight-gravelords"; slug="vampire-lord" },
    @{ src="yndrasta-the-celestial-spear.jpg";             faction="stormcast-eternals";       slug="yndrasta-the-celestial-spear" },
    @{ src="99120204017_DrycaHamadreth01.jpg";             faction="sylvaneth";                slug="drycha-hamadreth" },
    @{ src="morathi-khaine.jpg";                           faction="daughters-of-khaine";      slug="morathi-khaine" },
    @{ src="99129915028_KairosFateweaver01.jpg";           faction="disciples-of-tzeentch";    slug="kairos-fateweaver" }
)

$copied = 0
$missing = @()
$skipped = @()

foreach ($m in $mappings) {
    $src_path = Join-Path $downloads $m.src
    $ext = [System.IO.Path]::GetExtension($m.src)
    $faction_dir = Join-Path $units_base $m.faction
    $dst_path = Join-Path $faction_dir ($m.slug + $ext)

    if (-not (Test-Path $src_path)) {
        $missing += $m.src
        Write-Host "MISSING src: $($m.src)"
        continue
    }

    # Ensure faction dir exists
    if (-not (Test-Path $faction_dir)) {
        New-Item -ItemType Directory -Path $faction_dir -Force | Out-Null
    }

    # Check if dest already exists with same/larger size
    $src_size = (Get-Item $src_path).Length
    if (Test-Path $dst_path) {
        $dst_size = (Get-Item $dst_path).Length
        if ($dst_size -ge $src_size) {
            Write-Host "SKIP (dst larger/equal): $($m.slug)$ext ($dst_size >= $src_size)"
            $skipped += $m.slug
            $copied++  # count as done
            continue
        }
    }

    Copy-Item -Path $src_path -Destination $dst_path -Force
    $final_size = (Get-Item $dst_path).Length
    Write-Host "COPIED: $($m.src) -> $($m.faction)/$($m.slug)$ext ($final_size bytes)"
    $copied++
}

Write-Host ""
Write-Host "=== MISSION A SUMMARY ==="
Write-Host "Copied/OK: $copied / $($mappings.Count)"
Write-Host "Missing sources: $($missing.Count)"
if ($missing.Count -gt 0) { $missing | ForEach-Object { Write-Host "  MISSING: $_" } }
Write-Host "Skipped (already larger): $($skipped.Count)"

# Verify
Write-Host ""
Write-Host "=== VERIFICATION ==="
foreach ($m in $mappings) {
    $ext = [System.IO.Path]::GetExtension($m.src)
    $faction_dir = Join-Path $units_base $m.faction
    $dst_path = Join-Path $faction_dir ($m.slug + $ext)
    if (Test-Path $dst_path) {
        $sz = (Get-Item $dst_path).Length
        $ok = if ($sz -gt 10240) { "OK" } else { "SMALL!" }
        Write-Host "  $ok $($m.faction)/$($m.slug)$ext ($sz b)"
    } else {
        Write-Host "  MISSING: $($m.faction)/$($m.slug)$ext"
    }
}
