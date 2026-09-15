#
# ===== bennettAdventureFix (prototype v1) =====
#
# Bennett -> BennettAdventure, driven by the API's own parser, fixer and resource groups. A copy of
# yelanTranquilFix.py with this pair's tables; the machinery below "the tables" is that script's,
# unchanged, and anything learnt here should go back into both.
#
#   py -3 bennettAdventureFix.py <mod folder>                         fix every Bennett .ini under the folder
#   py -3 bennettAdventureFix.py <mod folder> --components Body,Bang  only some target components
#   py -3 bennettAdventureFix.py <mod folder> --keepBackups           keep the .ini backups the API makes
#   py -3 bennettAdventureFix.py <mod folder> --verbose               attach the API's logger
#   py -3 bennettAdventureFix.py <mod folder> --wsl                   from Windows: relaunch under WSL
#
# ---- What the frame analyses settled, and what is still a guess ----
#
# Read off FrameAnalysis-BennettAdventure-2026-09-14-044616 and FrameAnalysis-Bennett-2026-09-14-044301,
# so these are measurements rather than the Yelan analogy they started as:
#
#   * the skin draws FOUR slots -- Body A (first index 0) and B (44334), Bang A (0), Eye A (0);
#   * Body A, Body B and the Bang are all on the NORMAL-MAP shader 2c157719180b096c (bound LND:
#     lightmap ps-t0, normal map ps-t1, diffuse ps-t2), so all three want the ORFix three-register
#     layout. The Eye is on 95aa6cdb84eb7b99 with no normal map -- the plain NNFix layout;
#   * the Bang and the Eye have NO textures of their own: both read Body slot A's set (draws 49 and
#     48 bind 04cd73c6 / c3e39ad5 / bfa7fe04, which are A's lightmap / normal map / diffuse);
#   * BOTH characters bind the face diffuse at ps-t1, with the face LIGHT MAP d4841e1a at ps-t0
#     (main face draws 42/43/46/47/52/53 on the skin, 37/38/39 on Bennett) -- the GI 6.x face
#     register swap, and the reason both identity mods want --faceRegister ps-t1.
#
# **BENNETT HAS NO PLAIN BODY SLOT TO LAND ON, which Yelan did.** Tranquil's slot C was the
# no-normal-map variant matching Yelan's own shader family, and picking it is what stopped a hidden
# throat strip rendering as bright static. BennettAdventure has no such slot: A and B are both on the
# normal-map shader, so Bennett's model MUST be drawn through one, and the flat normal map this
# script creates is structural rather than cosmetic.
#
# ---- Which slot, and why no band lift: the measurement (2026-09-14) ----
#
# A GIMI lightmap's ALPHA is a material band selecting a shading ramp, and the bands here are
# discrete: 0, 78, 126-128, 176-178, 255. Histogrammed per band with the mean DIFFUSE under it:
#
#   Bennett body    0 (77%, dark cloth)  126-128 (white trim)  255 (12.5%, mean RGB 232/204/181,
#                                                              99.5% skin-coloured) = SKIN
#   Adventure A     0 (35%)  78  126-128  177-178 (30%, pale)  255 (7.3%, mean RGB 233/203/180,
#                                                              100% skin-coloured) = SKIN
#   Adventure B     0 (48%, orange 188/135/79)  78 (26%, blue 35/76/98)  126-128  176-178
#                   -- NO 255 BAND AT ALL, and nothing skin-coloured in any band
#
# So slot A is not the analogy to Yelan's, it is the measured answer twice over: it is the only Body
# slot with a skin band, and its skin band is at the SAME alpha as Bennett's with a diffuse mean
# matching to within 1/255 per channel. Drawing him through B would shade his face and arms with the
# outfit's ramps, which is the mistake Yelan's slot-B run made visible.
#
# And because the two skin bands already coincide, THERE IS NOTHING TO LIFT -- the Yelan pair needed
# a lift precisely because her skin sat at 115-127 and the target's at 255. Bennett's other bands
# (his white trim at 126-128) have no counterpart in A's legend, but a band the source never emits
# needs no mapping, and moving one on a guess is how the neck static was introduced there.
#
# ---- The Bang draws NOTHING, and that is the answer rather than a gap (2026-09-14) ----
#
# Yelan's Bang was a negative-index component: it drew the whole mod trimmed to its own bones, with
# those bones read off the REVERSE row (VGComponentSpec.secondary), because her bang bones had no
# forward row of their own. The split honours a secondary bone only on a vertex that ALSO carries a
# forward bone -- without that guard the whole face is drawn twice.
#
# Bennett cannot use that, and the reason is in his blend buffer: he has no hair bone. Group 0 is his
# head, and it carries 3225 vertices -- his hair AND his face. Groups 1 and 2 are his two eye bones
# (101 vertices each, weight exactly 1.0), and those are the whole of the rest of his head. All nine
# of the skin's Bang bones map back to exactly those three groups.
#
# So there is no partition that gives the Bang his hair without also giving it his face, his forward
# Bang row is empty, and an empty forward set means the guard above can never fire: the Bang would
# draw nothing whatever we did. The right answer is therefore to NOT FIX the Bang component at all --
# left unfixed its ib section keeps its `drawindexed = auto` and BennettAdventure keeps her own
# bangs, which is what you want when the source has no hair of its own to put there. Bennett's hair
# still arrives, drawn by the Body component along with the rest of his head.
#
# ---- Known wrong on the identity mod only: the face ----
#
# The face edit is a two-way ps-t0 <-> ps-t1 swap, which is what every shipped GI character does
# and is right for any mod authored before GI 6.x. The identity mod is built from a 6.x dump and
# already binds ps-t1, so the swap moves it the wrong way. The maintainer's call (2026-09-14) is
# to keep the identity mod at ps-t1 and add a heuristic guard to the swap later -- so until then,
# the identity mod's remapped face is knowingly wrong and everything else about it is not.
#
# **The texture recipe is deliberately EMPTY beyond the flat normal map.** Yelan's band lift, her
# alpha-1 head diffuse and her vertex-colour edit were each derived from her own pair in game, and
# none of them is known to apply here. Add them one at a time, each with a measurement behind it.
#

import argparse
import os
import re
import sys
from typing import Dict, List, Optional

import numpy as np

OnWindows = (sys.platform == "win32")


def winToPosix(path: str) -> str:
    """`E:\\a\\b` -> `/mnt/e/a/b` on Linux (WSL's default drive mounts); any other path is returned as is"""
    if (OnWindows or (len(path) < 2) or (path[1] != ":") or (not path[0].isalpha())):
        return path
    return "/mnt/" + path[0].lower() + path[2:].replace("\\", "/")


Repo = os.environ.get("AG_REMAP_REPO") or winToPosix(r"E:\Computer\Games\Genshin\Repos\Repos\Fix-Raiden-Boss")
APISrc = os.path.join(Repo, "Anime Game Remap (for all users)", "api", "src", "py")
if (not os.path.isdir(APISrc)):
    raise SystemExit(f"the API's package folder is not at {APISrc}; set AG_REMAP_REPO to the repo's path on this OS")
sys.path.insert(0, APISrc)
if (hasattr(os, "add_dll_directory")):
    os.add_dll_directory(os.path.join(APISrc, "FixRaidenBoss2"))

import FixRaidenBoss2 as FRB     # noqa: E402
from PIL import Image            # noqa: E402

for needed in ("VGComponentSplit", "VGSplitGroupResource", "BufReplace"):
    if (not hasattr(FRB, needed)):
        raise SystemExit(f"this API build has no {needed}: it needs the core built after 2026-09-12 (the component split)")


# ============================================================================== the pair

V = "6.1"
NNFix = "CommandList\\global\\ORFix\\NNFix"
ORFix = "CommandList\\global\\ORFix\\ORFix"

# Bennett's hashes are the CURRENT model's: his hash.json moved three times inside the library's
# window (draw_vb at 4.1, ib at 4.3, position_vb at 4.4), and these are the post-4.4 values, which
# are what a mod built on today's model carries. ibOld is his pre-4.3 ib, for a mod that predates it.
Bennett = {"draw_vb": "02cf3aa5", "position_vb": "6cff51b4", "blend_vb": "d4acf3f7", "texcoord_vb": "acde80a4",
           "ib": "cdc66323", "ibOld": "f51209fc", "tex_face_diffuse": "50f7dc9a",
           "objects": {0: "head", 9879: "body"}}

Adventure = {"Body": {"draw_vb": "bc87167b", "position_vb": "14efbc45", "blend_vb": "09b92379", "texcoord_vb": "51dd19aa", "ib": "022a9ccd",
                      "slots": {"A": 0, "B": 44334}},
             "Bang": {"draw_vb": "2f953b46", "position_vb": "a8a0adb9", "blend_vb": "d2bb6147", "texcoord_vb": "5a79eaa8", "ib": "43ad99d1",
                      "slots": {"A": 0}},
             "Eye": {"draw_vb": "feb0e532", "position_vb": "f5dd3d9e", "blend_vb": "89827a3f", "texcoord_vb": "941adcbf", "ib": "91b4d5dd",
                     "slots": {"A": 0}}}
AdventureFaceDiffuse = "2b1b2edf"

# Per target component: which strategy splits the mod's triangles for it, which of the target's draw
# slots the mod is drawn through, and the slot's register layout -- every field measured off the
# frame analysis (see the header), the Body's choice of slot A included -- it is the only Body slot
# with a skin band, and its skin band sits at the same alpha as Bennett's.
#
# The Bang is negative-index for the reason Tranquil's was, only more so: the vertex-group table has
# NO forward Bennett -> Bang row at all (all nine of its groups correspond to his three head bones,
# so the correspondence exists only in reverse). Its bones come entirely from the reverse row via
# VGComponentSpec.secondary, and without that it would draw nothing.
Plan = {"Body": {"strategy": "graphcut", "slot": "A", "normalMap": True, "fix": ORFix, "face": True},
        "Bang": {"strategy": "negative", "slot": "A", "normalMap": True, "fix": ORFix, "face": False},
        "Eye": {"strategy": "graphcut", "slot": "A", "normalMap": False, "fix": NNFix, "face": False}}

# NO BAND LIFT YET. On Yelan this is where her legend was mapped onto Tranquil's, band by band, and
# the lift is applied to every object's lightmap. Bennett's and BennettAdventure's legends have not
# been measured against each other in game, so nothing is moved: a wrong lift is not a no-op, it
# puts alpha 0 on a band that meant something (Yelan's neck static). Measure first, then fill in.
SkinBand = None
FurBand = None


def skinColoured(rgb) -> "np.ndarray":
    """Where a diffuse (H x W x 3, uint8) is skin-coloured: warm and bright, red over green over blue"""
    r, g, b = (rgb[..., i].astype(np.int16) for i in range(3))
    return (r >= 96) & (r >= g) & (g >= b) & ((r - b) >= 16) & ((r - b) <= 140)
# The flat normal map the reference draws with is 127 / 127 / 255 under a BC7_UNORM_SRGB header; a created
# texture is written untagged, so it carries what that samples as: round(255 * (127 / 255) ** 2.2) = 55
FlatNormal = (55, 55, 255, 255)

targetName = lambda component: "BennettAdventure" + component
keepName = lambda name: name


# ============================================================================== the tables

def registerBennett(components: List[str]) -> FRB.ModType:
    """Bennett and one pseudo target per component, as a runtime ModType on the shipped GI builders"""
    FRB.CppGlobalModTypes.registerAll()
    shared = FRB.CppGlobalModTypes.all()[0].vgRemaps
    GI, YID = int(FRB.GameTypeId.GI), int(FRB.ModTypeId.Bennett)

    hashRows = [([V, "Bennett", key], Bennett[key]) for key in ("draw_vb", "position_vb", "blend_vb", "texcoord_vb", "ib", "tex_face_diffuse")]
    # No index rows for the pseudo targets: nothing looks them up (RegNewVals writes the index from
    # the table above), and a reverse lookup of "0" that could land on a target row blinds the
    # classifier and GIMIObjPartFilter's window
    indexRows = [([V, "Bennett", "", obj], str(index)) for index, obj in Bennett["objects"].items()]
    vg = shared.clone()
    for component in components:
        target = targetName(component)
        hashRows += [([V, target, key], Adventure[component][key]) for key in ("draw_vb", "position_vb", "blend_vb", "texcoord_vb", "ib")]
        hashRows.append(([V, target, "tex_face_diffuse"], AdventureFaceDiffuse))
        row = shared.get(["Bennett", "", "BennettAdventure", component], ["1.0", "5.7"], errorOnNotFound = False)
        if (row is None):
            raise SystemExit(
                f"the vertex group table has no Bennett -> BennettAdventure {component} row, so nothing of\n"
                f"his model belongs to that component. For the Bang that is the MEASURED answer rather than a\n"
                f"gap (see the header): drop it from --components and the skin keeps its own bangs.")
        vg.addRows([(["1.0", "Bennett", "", V, target, ""], dict(row.remap))])

    targets = [targetName(c) for c in components]
    hashes = FRB.Hashes({"Bennett": targets}); hashes.addRepoRows(hashRows)
    indices = FRB.Indices({"Bennett": targets}); indices.addRepoRows(indexRows)
    modType = FRB.ModType(GI, YID, "Bennett", [], hashes, indices, None, vg)
    template = next(m for m in FRB.CppGlobalModTypes.all() if m.name == "Keqing")   # any shipped GI type: its builders are the table builders, which consult the overrides
    modType.iniParseBuilder = template.iniParseBuilder
    modType.iniFixBuilder = template.iniFixBuilder
    modType.iniRemoveBuilder = template.iniRemoveBuilder
    FRB.ModTypeIdTools.registerModType(modType)
    FRB.CppGlobalModTypes.registerMissing()
    return modType


def componentSpecs(components: List[str]) -> List[FRB.VGComponentSpec]:
    """
    Every component of the target, from the API's shared table: the forward row is the component's
    bones, and for a negative-index component the REVERSE row turned around is its secondary bones
    (every one of the Bang's nine bones is one of Bennett's three head bones, and the forward table
    has no Bennett -> Bang row at all, so WITHOUT this the Bang draws nothing)
    """
    shared = FRB.CppGlobalModTypes.all()[0].vgRemaps
    specs = []
    for component in components:
        forward = dict(shared.get(["Bennett", "", "BennettAdventure", component], ["1.0", "5.7"], errorOnNotFound = False).remap)
        secondary = {}
        if (Plan[component]["strategy"] == "negative"):
            reverse = shared.get(["BennettAdventure", component, "Bennett", ""], ["1.0", "5.7"], errorOnNotFound = False)
            if (reverse is not None):
                for bone, source in reverse.remap.items():
                    if (source not in forward and source not in secondary):
                        secondary[source] = bone
        specs.append(FRB.VGComponentSpec(component, forward, secondary = secondary, negativeIndex = Plan[component]["strategy"] == "negative"))
    return specs


# ============================================================================== the parser

def makeParser(modType: FRB.ModType):
    """
    The same parser makeGIMICharParser builds, assembled from Python so the fixer can reach its
    IniFile: a GIMIParser whose sections are sorted by the API's hash / index classifier -- the
    drawn objects by the shared ib hash plus their match_first_index, everything else by a hash of
    its own
    """
    drawnObjs = [("", name) for name in Bennett["objects"].values()]
    hashOnly = {"ib": ("", "ib"), "blend_vb": ("", "blend"), "position_vb": ("", "position"), "texcoord_vb": ("", "texcoord"),
                "draw_vb": ("", "other"), "tex_face_diffuse": ("", "face")}
    modObjs = drawnObjs + [obj for obj in hashOnly.values() if (obj not in drawnObjs)]

    def factory(iniFile, modTypeId):
        classifier = FRB.GIMISectionClassifier(dict(hashOnly), modType.hashes, {"ib": {obj: obj for obj in drawnObjs}}, modType.indices, None)
        # Reverse lookups filtered to Bennett's own rows: the pseudo targets share hash types with him
        classifier.hashNonVersionVals = {"name": "Bennett"}
        classifier.indexNonVersionVals = {"name": "Bennett"}
        parser = FRB.GIMIParser(iniFile, modObjs = modObjs, objTargetFuncs = [classifier], modTypeId = modTypeId)
        parser.trackKeys = True
        parser.keysToTrack = {"hash", "match_first_index"}
        _alive.append(classifier)
        return parser
    return factory


# ============================================================================== the mod

class ModFiles():
    """
    One mod's files, read out of the API's parsed sections, and what each component of the target
    would draw of it -- computed once per .ini, shared by the component fixers. The fixer factories
    run BEFORE the parser parses, so the files are found by hash over IniFile.getIfTemplates() rather
    than through the parser's graphs
    """

    def __init__(self, ini, components: List[str]):
        self.folder = os.path.dirname(os.path.abspath(ini.file))
        self.position, self.blend, self.texcoord, self.objects, self.face = self._readFiles(ini)
        rel = lambda p: os.path.relpath(p, self.folder) if p else "-"
        print(f"  files: position {rel(self.position)}, blend {rel(self.blend)}, texcoord {rel(self.texcoord)}, face diffuse {rel(self.face)}")
        for name, o in self.objects.items():
            print(f"    {name}: ib {rel(o['ib'])}; diffuse {rel(o['Diffuse'])}; lightmap {rel(o['LightMap'])}")
        for label, f in (("position", self.position), ("blend", self.blend), ("texcoord", self.texcoord)):
            if (not f):
                raise ValueError(f"the .ini names no {label} buffer for Bennett")
        if (not self.objects):
            raise ValueError("the .ini has no object sections on Bennett's IB hash")

        # The split, once, to know what each component draws (the fixer needs it before any resource
        # exists); the grouped resource redoes it in C++ when it writes the files
        blendRaw = np.frombuffer(open(self.blend, "rb").read(), dtype = np.uint8)
        if (len(blendRaw) % 32):
            raise ValueError(f"'{self.blend}' is not a whole number of 32-byte lines")
        rows = blendRaw.reshape(-1, 32)
        weights = rows[:, :16].copy().view("<f4").reshape(-1, 4)
        indices = rows[:, 16:].copy().view("<i4").reshape(-1, 4)
        self.vertexCount = len(rows)
        self.ibNames = [name for name, o in self.objects.items() if (o["ib"])]
        self.ibPaths = [self.objects[name]["ib"] for name in self.ibNames]
        ibs = [np.frombuffer(open(p, "rb").read(), dtype = "<u4").reshape(-1, 3).tolist() for p in self.ibPaths]
        self.texcoordStride = os.path.getsize(self.texcoord) // self.vertexCount if (self.vertexCount) else 0
        self.positionStride = os.path.getsize(self.position) // self.vertexCount if (self.vertexCount) else 0
        print(f"  buffers: {self.vertexCount} vertices, texcoord stride {self.texcoordStride}; triangles " + ", ".join(f"{n} {len(ib)}" for n, ib in zip(self.ibNames, ibs)))

        self.components = components
        self.specs = componentSpecs(components)
        split = FRB.VGComponentSplit(weights.tolist(), indices.tolist(), ibs, self.specs)
        self.results: Dict[str, FRB.VGComponentBuffers] = {c: split.split(c) for c in components}
        for c, r in self.results.items():
            s = r.stats
            kept = ", ".join(f"{n} {k}" for n, k in zip(self.ibNames, s.trianglesKept))
            print(f"  {c} ({Plan[c]['strategy']}): vertices {s.keptVertices} of {s.vertexCount}; triangles {kept}"
                  + (f"; sentinels {s.sentinels}" if (Plan[c]["strategy"] == "negative") else f"; renormalised {s.renormalised}, neighbour-skinned {s.neighbourSkinned}"))
        for i, name in enumerate(self.ibNames):
            drawnBy = np.zeros(len(ibs[i]), dtype = int)
            for c, r in self.results.items():
                keys = {tuple(t) for t in (np.array(r.vertices)[np.array(r.ibs[i], dtype = np.int64)].tolist() if (len(r.ibs[i]) and Plan[c]["strategy"] == "graphcut") else r.ibs[i])}
                drawnBy += np.array([tuple(t) in keys for t in ibs[i]], dtype = int) if keys else 0
            print(f"  coverage {name}: {len(ibs[i])} triangles, drawn by nobody {int((drawnBy == 0).sum())}, by more than one {int((drawnBy > 1).sum())}")

        self._sizes: Dict[str, tuple] = {}

    def _readFiles(self, ini):
        templates = ini.getIfTemplates()

        def first(template, key) -> Optional[str]:
            for p in template.parts:
                if (hasattr(p, "getVals")):
                    vals = p.getVals(key)
                    if (vals):
                        return vals[0].strip()
            return None

        def fileOf(resource: Optional[str]) -> Optional[str]:
            if (not resource or resource.lower() == "null" or resource not in templates):
                return None
            f = first(templates[resource], "filename")
            return os.path.normpath(os.path.join(self.folder, f.replace("\\", os.sep))) if f else None

        position = blend = texcoord = face = None
        objects: Dict[str, Dict[str, Optional[str]]] = {}
        for template in templates.values():
            h = (first(template, "hash") or "").lower()
            if (h == Bennett["position_vb"]):
                position = position or fileOf(first(template, "vb0"))
            elif (h == Bennett["blend_vb"]):
                blend = blend or fileOf(first(template, "vb1"))
            elif (h == Bennett["texcoord_vb"]):
                texcoord = texcoord or fileOf(first(template, "vb1"))
            elif (h == Bennett["tex_face_diffuse"]):
                # BOTH registers: a mod authored pre-6.x binds its face diffuse at ps-t0, one built
                # from a 6.x dump (an identity mod, say) at ps-t1. Reading only ps-t0 silently
                # reported "face diffuse -" on the latter.
                face = face or fileOf(first(template, "ps-t0")) or fileOf(first(template, "ps-t1"))
            elif (h in (Bennett["ib"], Bennett["ibOld"])):
                index = first(template, "match_first_index")
                if (index is None):
                    continue
                name = Bennett["objects"].get(int(index))
                if (name is None):
                    print(f"  ! {template.name}: match_first_index {index} is not one of Bennett's objects, skipped")
                    continue
                objects[name] = {"ib": fileOf(first(template, "ib")), "Diffuse": fileOf(first(template, "ps-t0")), "LightMap": fileOf(first(template, "ps-t1"))}
        objects = {name: objects[name] for _, name in sorted(Bennett["objects"].items()) if (name in objects)}
        return position, blend, texcoord, objects, face

    def drawn(self, component: str) -> List[str]:
        """The mod objects with at least one triangle in this component, in draw order"""
        kept = self.results[component].stats.trianglesKept
        return [name for name, n in zip(self.ibNames, kept) if (n > 0)]

    def keptVertices(self, component: str) -> int:
        return self.results[component].stats.keptVertices

    def objectOf(self, path: str, kind: str) -> Optional[str]:
        for name, o in self.objects.items():
            if (o[kind] and os.path.normcase(os.path.abspath(o[kind])) == os.path.normcase(os.path.abspath(path))):
                return name
        return None

    def textureSize(self, name: str) -> tuple:
        """(width, height) of the object's diffuse, for the flat normal map created beside it"""
        if (name not in self._sizes):
            path = self.objects[name]["Diffuse"]
            with Image.open(path) as image:
                self._sizes[name] = image.size
        return self._sizes[name]

    def texcoordLineEdit(self):
        """
        UNUSED IN v1, kept as the hook. On the Yelan pair this normalised the per-vertex data the
        target's shader reads and the source's does not -- vertex colour G = B = 128 (that mod
        carried 188) and a zeroed second UV set. Measure Bennett's before enabling it.
        """
        stride = self.texcoordStride
        def edit(line: bytes) -> bytes:
            out = bytearray(line)
            out[1] = 128
            out[2] = 128
            if (stride == 20):
                out[12:20] = bytes(8)
            return bytes(out)
        return edit


# ============================================================================== the textures

def alphaOne(texFile) -> None:
    """UNUSED IN v1. On the Yelan pair the target's shader darkens by diffuse alpha and the source's
    ignores it, so her head diffuse was forced to alpha 1. Not measured on Bennett."""
    texFile.img.putalpha(1)


def liftBands(diffusePath: Optional[str]):
    """
    UNUSED IN v1, and it RAISES if called, because SkinBand / FurBand are None until the two
    legends have been measured against each other. On the Yelan pair this moved her bands onto the
    target's -- fur 255 -> 0, then skin 115-127 -> 255 where the diffuse agreed the pixel was skin.
    """
    def lift(texFile) -> None:
        if (SkinBand is None or FurBand is None):
            raise SystemExit("liftBands: Bennett's and BennettAdventure's band legends have not been "
                             "measured; fill in SkinBand / FurBand before enabling the lift")
        pixels = np.array(texFile.img)
        alpha = pixels[..., 3]
        fur = (alpha == FurBand[0])
        skin = (alpha >= SkinBand[0]) & (alpha <= SkinBand[1])
        if (diffusePath and os.path.isfile(diffusePath)):
            diffuse = FRB.TextureFile(diffusePath, readPillowImg = True)
            diffuse.open()
            if (diffuse.hasImage):
                img = diffuse.img.convert("RGB")
                if (img.size != texFile.img.size):
                    img = img.resize(texFile.img.size, Image.BILINEAR)
                skin &= skinColoured(np.asarray(img))
        alpha[fur] = FurBand[1]
        alpha[skin] = SkinBand[2]
        texFile.img = Image.fromarray(pixels, "RGBA")
    return lift


# ============================================================================== the fixers

_files: Dict[str, ModFiles] = {}
_alive: List[object] = []          # every edit handed to the API, kept alive for the run
_written = set()                   # texture files written this run (one edit of one texture serves every component)


def filesFor(ini, components: List[str]) -> ModFiles:
    key = os.path.normcase(os.path.abspath(ini.file))
    if (key not in _files):
        print(f"{os.path.basename(ini.file)}:")
        _files[key] = ModFiles(ini, components)
    return _files[key]


def texReplace(files: ModFiles, resModObj, kind: str, filterFunc) -> FRB.TexReplace:
    """A texture edit through the API's Pillow-engine TexEditor, written once per source texture"""
    def fix(resource) -> bool:
        if (resource.fixedPath in _written):
            return True
        _written.add(resource.fixedPath)
        # The Compressonator engine, not Pillow: it reads the DX10 header, and a BC7_UNORM_SRGB source
        # (the head diffuse) gets the 1/2.2 pre-correction baked in on the way out, since the file is
        # written back untagged. Pillow writes a legacy header with the values untouched, and the
        # shader then samples them without the sRGB decode: a visibly brighter texture in game.
        # mipmaps: every texture the game ships carries its chain, and one written without it is
        # sampled from its top level at every distance -- speckles over the hair (2026-09-12)
        editor = FRB.TexEditor([filterFunc], readPillowImg = True, compress = True, mipmaps = True)
        editor.fix(FRB.TextureFile(resource.srcPath, readPillowImg = True), resource.fixedPath)
        return True
    placeholder = FRB.TexEditor([], compress = True)
    return FRB.TexReplace(resModObj, placeholder, fixFunc = fix, resSubType = kind)


def makeFixer(component: str, components: List[str]):
    plan = Plan[component]
    slot, slotObj = plan["slot"], ("", plan["slot"])
    naming = FRB.CppIniNamingTools

    def factory(parser, toModName: str, modTypeId: int):
        ini = parser._iniFile
        modType = FRB.ModTypeIdTools.getModType(modTypeId)
        files = filesFor(ini, components)
        drawn = files.drawn(component)
        cut = plan["strategy"] == "graphcut"
        groups = max(len(drawn), 1)
        print(f"  {toModName}: draws {', '.join(drawn) or 'nothing'} through slot {slot}" + (f" ({groups} .ini groups)" if (groups > 1) else ""))

        # ---- 1. copy each drawn object's graph onto the component's draw slot ----
        #
        # Every drawn object goes to the SAME slot; the second claimant lands in group 1, which is a
        # second .ini file (the API's merge shape). Every other graph is copied unrenamed into every
        # group, exactly as the shipped template does, so each file is complete on its own.
        remap = {}
        for name in Bennett["objects"].values():
            remap[(0, "", name)] = [(0, "", slot)] if (name in drawn) else []
        for kind in ("ib", "blend", "position", "texcoord", "other", "face"):
            wanted = drawn and (kind != "face" or plan["face"])
            remap[(0, "", kind)] = [(0, "", kind, keepName) for _ in range(groups)] if wanted else []
        edits: List[object] = [FRB.GraphGroupRemap(remap = remap)]

        for g, name in enumerate(drawn):
            # ---- 2. the textures: edit, then the flat normal map where the slot reads one ----
            if (plan["normalMap"]):
                # NO TEXTURE EDITS IN v1, deliberately. Yelan's recipe edits the head diffuse to
                # alpha 1 and lifts every lightmap band to band here; both were derived from HER
                # pair in game and neither is known to hold for Bennett. The mod's own textures pass
                # through untouched until a measurement says otherwise -- see the file header.
                #
                # What remains is structural, not cosmetic: Bennett is drawn by the plain two-register
                # shader (ps-t0 diffuse, ps-t1 lightmap) and every Body / Bang slot of the skin is on
                # the three-register normal-map one, so the registers have to be SHIFTED and a normal
                # map supplied. ps-t0 is duplicated onto a scratch register that the created normal
                # map then replaces; the main edit renames it back to ps-t0 once the shift is done
                edits.append(FRB.GraphGroupEdit([{slotObj: [FRB.RegRemap({"ps-t0": ["ps-t1", "ps-tNormal"], "ps-t1": ["ps-t2"]})]} if (i == g) else {} for i in range(groups)]))
                creator = FRB.TexCreator(1024, 1024, FRB.CppColour(*FlatNormal), compress = True, mipmaps = True)   # flat: any size serves every object
                edits.append(FRB.ResRegCollect({(g, "", slot): "ps-tNormal"}, {"normalMap": FRB.TexCreate((g, "", slot + "RemapNormal"), "NormalMap", creator)}))

        # ---- 3. the buffers, as ONE resource group: split together by VGSplitGroupResource ----
        #
        # The collect splices the collected register into an `if 1 ... endif` block, which splits the
        # section into parts; the draw call below is filled with RegFillMissingMode.BottomCover (a
        # fresh LAST part) so it still lands after the ib and the textures whatever the order here.
        #
        # The blend, the texcoord and this object's ib, plus the position for a cut component (a
        # negative-index component draws every vertex, so it keeps the mod's own Position.buf).
        # Every drawn object's ib is handed to the group, whether or not this group holds it: the
        # vertex set is the union over all of them.
        for g, name in enumerate(drawn):
            kinds = {"blend": ((g, "", "blend"), "vb1"), "texcoord": ((g, "", "texcoord"), "vb1"), "ib": ((g, "", slot), "ib")}
            if (cut):
                kinds["position"] = ((g, "", "position"), "vb0")
            srcRegs, resEdits = {}, {}
            for kind, (srcGraph, reg) in kinds.items():
                resObj = (g, "", f"{slot}Remap{kind.capitalize()}")
                srcRegs[resObj] = {srcGraph: reg}
                resEdits[resObj] = {component: FRB.BufReplace(resObj, kind, resSubType = name if (kind == "ib") else None)}
            builder = FRB.IniGroupedResBuilder(FRB.VGSplitGroupResource, args = [f"Bennett{toModName}Buffers"],
                                               kwargs = {"component": component, "specs": files.specs, "ibPaths": files.ibPaths,
                                                         "texcoordLineEdit": files.texcoordLineEdit()})
            edits.append(FRB.ResGroupCollect([component], srcRegs, resEdits, {component: builder}, id = g))

        # ---- 4. the index, windowed to the copied object's own KVPs (head and body share the ib hash) ----
        objFilter = FRB.GIMIObjPartFilter(modType.hashes, modType.indices, {"ib"}, None)
        _alive.append(objFilter)          # filter() hands out callables that point back at it; let it outlive this factory
        indexEdits, indexFilters, indexKeys, indexTrack = [], [], [], []
        for g, name in enumerate(drawn):
            indexEdits.append({slotObj: [FRB.RegNewVals({"match_first_index": str(Adventure[component]["slots"][slot])})]})
            indexFilters.append({slotObj: [objFilter.filter(("", name))]})
            indexKeys.append({slotObj: objFilter.keysToTrack()})
            indexTrack.append({slotObj: True})
        if (drawn):
            edits.append(FRB.GraphGroupEdit(indexEdits, trackKeys = indexTrack, keysToTrack = indexKeys, keyFilters = indexFilters))

        # ---- 5. everything else, per group ----
        rename = FRB.GraphRename(lambda n: naming.getRemapFixName(n, toModName))
        hashRemap = FRB.RegAssetRemap({"hash": (modType.hashes, "HashNotFound")}, toModName, "Bennett", ini.fromVersion, ini.toVersion)
        dropFixCalls = FRB.RegRemove({"run": lambda _ind, val: val in (NNFix, ORFix)})
        fillDraw = FRB.RegFillMissing("drawindexed", "auto", fillMode = FRB.RegFillMissingMode.BottomCover)   # the draw call moves onto each object, at its END...
        removeDraw = FRB.RegRemove({"drawindexed": None})                      # ...and off the shared ib section, which now only skips
        addFix = FRB.RegDelimitedAdd([("run", plan["fix"])], {"drawindexed": []}, pathEndOnlyWhenUndelimited = True,
                                    mode = FRB.RegDelimitedAddMode.PerPath)   # ONE call per path: NNFix/ORFix re-slot the ps-t registers, so two undo each other
        normalBack = FRB.RegRemap({"ps-tNormal": ["ps-t0"]})
        perGroup = []
        for g in range(groups):
            group = {slotObj: [dropFixCalls] + ([normalBack] if plan["normalMap"] else []) + [fillDraw, addFix, hashRemap],
                     ("", "ib"): [FRB.GraphRename(lambda n: naming.getRemapIbName(n, toModName)), hashRemap, removeDraw],
                     ("", "blend"): [FRB.GraphRename(lambda n: naming.getRemapBlendName(n, toModName)), hashRemap]
                                    + ([FRB.RegNewVals({"draw": f"{files.keptVertices(component)},0"})] if cut else []),
                     ("", "position"): [rename, hashRemap],
                     ("", "texcoord"): [rename, hashRemap],
                     ("", "other"): [rename, hashRemap,
                                     FRB.RegNewVals({"override_byte_stride": str(files.positionStride), "override_vertex_count": str(files.keptVertices(component))},
                                                    addNewKVPs = True)]}
            if (plan["face"]):
                # The two-way face swap every shipped GI character carries: GI 6.x swapped which
                # register the shader reads the face diffuse and the face light map out of, so a mod
                # binding its diffuse at ps-t0 has to be moved to ps-t1.
                #
                # It is a SWAP, so it also moves an already-correct ps-t1 back to ps-t0. That is right
                # for the mods this runs on -- essentially all of them predate 6.x -- and wrong for a
                # mod built from a 6.x dump, which is what the identity mod is. Measured on both
                # characters 2026-09-14: the game binds the face diffuse at ps-t1 and the face light
                # map (d4841e1a, shared by the two skins) at ps-t0.
                #
                # THE IDENTITY MOD STAYS AT ps-t1 (maintainer, 2026-09-14) and this swap stays
                # unguarded for now; a HEURISTIC GUARD is deferred work. So when testing the identity
                # mod in game, its remapped FACE is the one part that is knowingly wrong -- judge the
                # face on a real mod instead, and do not "correct" the swap on the strength of it.
                #
                # What the guard has to decide is which register the MOD binds its face diffuse on,
                # and normalise to ps-t1 rather than swapping blind:
                #   * the section's own registers are readable here -- ModFiles already looks for the
                #     face file on ps-t0 and then ps-t1 (see _readFiles), so the binding register is
                #     known at the point the edit is built;
                #   * a mod that binds ps-t0 needs the move, a mod already on ps-t1 needs nothing,
                #     and a mod binding BOTH is a real case (some carry a light map too) -- that one
                #     wants the swap, since its ps-t0 really is a diffuse in the old convention;
                #   * it belongs in the shipped GIMICharFixerConfig (swapFaceRegs) as well, not just
                #     here, because every one of the 44 compiled characters carries the same swap.
                group[("", "face")] = [rename, hashRemap, FRB.RegRemap({"ps-t0": ["ps-t1"], "ps-t1": ["ps-t0"]})]
            perGroup.append(group)
        if (drawn):
            edits.append(FRB.GraphGroupEdit(perGroup))

        _alive.extend(edits)
        fixer = FRB.GIMIFixer(parser, graphGroupEdits = edits, modsToFix = [toModName])
        _alive.append(fixer)
        return fixer
    return factory


# ============================================================================== run

def main():
    parser = argparse.ArgumentParser(description = "Bennett -> BennettAdventure, through the API's parser, fixer and resource groups")
    parser.add_argument("mod", help = "the mod folder (every Bennett .ini under it is fixed)")
    parser.add_argument("--components", default = "Body,Eye", help = "target components to produce (default: %(default)s -- the Bang is left alone on purpose, see the header)")
    parser.add_argument("--keepBackups", action = "store_true", help = "keep the .ini backups the API makes")
    parser.add_argument("--verbose", action = "store_true", help = "attach the API's logger")
    parser.add_argument("--loop", action = "store_true", help = "drive parse / fix / resources per .ini from this script instead of RemapService")
    parser.add_argument("--wsl", action = "store_true", help = "from Windows: run this same command under WSL, where the core is built (AG_REMAP_WSL_DISTRO / AG_REMAP_WSL_VENV)")
    args = parser.parse_args()
    if (args.wsl):
        raise SystemExit(relaunchUnderWsl(args))
    args.mod = winToPosix(args.mod)
    components = [c.strip() for c in args.components.split(",") if c.strip()]
    unknown = [c for c in components if (c not in Plan)]
    if (unknown):
        raise SystemExit(f"unknown component(s) {unknown}; choose from {list(Plan)}")

    modType = registerBennett(components)
    FRB.CppStrategyOverrides.clear()
    FRB.CppStrategyOverrides.setParser("Bennett", makeParser(modType))
    for component in components:
        FRB.CppStrategyOverrides.setFixer("Bennett", targetName(component), makeFixer(component, components))

    try:
        if (args.loop):
            fixFolder(os.path.abspath(args.mod), args)
        else:
            runService(os.path.abspath(args.mod), args)
    finally:
        FRB.CppStrategyOverrides.clear()


def relaunchUnderWsl(args) -> int:
    """
    Run this script again inside WSL with the same arguments (minus --wsl): the venv's python, the
    script and the mod folder addressed through /mnt/<drive>/..., the repo through AG_REMAP_REPO
    """
    import shlex
    import subprocess

    if (not OnWindows):
        raise SystemExit("--wsl is for a Windows shell; this is already Linux")
    distro = os.environ.get("AG_REMAP_WSL_DISTRO", "Ubuntu-22.04")
    venv = os.environ.get("AG_REMAP_WSL_VENV", "~/agremap-venv")
    toPosix = lambda p: "/mnt/" + p[0].lower() + p[2:].replace("\\", "/")
    script = toPosix(os.path.abspath(__file__))
    mod = toPosix(os.path.abspath(args.mod))
    repo = toPosix(os.path.abspath(Repo))
    flags = [f"--components={args.components}"] + [f"--{name}" for name in ("keepBackups", "verbose", "loop") if getattr(args, name)]
    command = f"source {venv}/bin/activate && AG_REMAP_REPO={shlex.quote(repo)} python {shlex.quote(script)} {shlex.quote(mod)} {' '.join(flags)}"
    print(f"wsl -d {distro}: {command}")
    return subprocess.call(["wsl", "-d", distro, "--", "bash", "-lc", command])


def runService(folder: str, args) -> None:
    """The whole run through RemapService: folder walk, undo of a previous fix, backups, resources, summary"""
    service = FRB.RemapService(path = folder, keepBackups = args.keepBackups, forcedModTypeIds = {int(FRB.ModTypeId.Bennett)},
                               logger = FRB.Logger() if args.verbose else None)
    service.fix()
    stats = service.stats
    print(f"\n.ini fixed: {len(stats.ini.fixed)}, skipped: {len(stats.ini.skipped)}")
    for path, error in stats.ini.skipped.items():
        print(f"  SKIPPED {os.path.relpath(path, folder)}: {error}")
    for label in ("blend", "position", "texcoord", "buf", "texEdit", "texAdd"):
        s = getattr(stats, label)
        print(f"{label}: fixed {len(s.fixed)}, skipped {len(s.skipped)}")
        for path in sorted(s.fixed):
            print(f"  {os.path.relpath(path, folder)}")
        for path, error in s.skipped.items():
            print(f"  SKIPPED {os.path.relpath(path, folder)}: {error}")


def fixFolder(folder: str, args) -> None:
    """
    Every .ini under the folder, through the API: undo a previous fix, parse, fix, then fix the
    resources the fix collected -- the same sequence RemapService runs, minus the service (for an API
    whose service loop predates the 2026-09-12 fixFunc fix)
    """
    YID = int(FRB.ModTypeId.Bennett)
    fixed, skipped, written, failed = [], {}, [], []
    for root, _, names in os.walk(folder):
        for name in sorted(names):
            if (not name.lower().endswith(".ini") or name.upper().startswith("DISABLED")):
                continue
            if (re.search(r"RemapFix\d+\.ini$", name, re.IGNORECASE)):
                os.remove(os.path.join(root, name))        # a merge's extra file from a previous run; the fix writes it again
                continue
            path = os.path.join(root, name)
            try:
                ini = FRB.IniFile(file = path, forcedFromModTypeIds = {YID})
                ini.removeFix(False, True, False, args.keepBackups)
                ini.clearModels()
                ini.parse()
                ini.fix(keepBackup = args.keepBackups)
            except Exception as e:
                skipped[path] = e
                print(f"  SKIPPED {os.path.relpath(path, folder)}: {type(e).__name__}: {e}")
                continue
            fixed.append(path)
            for resource in list(ini.getResources()) + list(ini.getGroupedResources()):
                try:
                    ok = resource.fix()
                except Exception as e:
                    ok = False
                    print(f"  ! {getattr(resource, 'name', getattr(resource, 'fixedPath', '?'))}: {type(e).__name__}: {e}")
                members = resource.memberResources() if hasattr(resource, "memberResources") else [resource]
                for member in members:
                    (written if ok else failed).append(getattr(member, "fixedPath", member.srcPath))
    print(f"\n.ini fixed: {len(fixed)}, skipped: {len(skipped)}")
    print(f"resources written: {len(set(written))}, failed: {len(failed)}")
    for path in sorted(set(written)):
        print(f"  {os.path.relpath(path, folder)}")
    for path in failed:
        print(f"  FAILED {os.path.relpath(path, folder)}")


if (__name__ == "__main__"):
    main()
