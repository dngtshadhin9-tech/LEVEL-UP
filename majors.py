"""
majors.py — MajorLogin + GetLoginData (config, payload builder, HTTP senders)

app.py theke kata hoyeche. Ekhane sob login-related config ek jayga-te:
  * MAJORLOGIN_HOST / clientbp host / path / ban-status sets / response offset scan limit
  * REAL_CLIENT_PROFILE (OB55 capture), _DEVICE_POOL (per-UID device)
  * build_majorlogin_payload(), send_majorlogin(), send_getlogin()

app.py runtime object-gulo (client, headers, aes_encrypt, report_fail ...) configure()-er
maddhome inject kore, tai circular import hoy na (app.py __main__ hishebe chole).
Logic hubohu agerta-i; kono behaviour change kora hoyni.
"""
import os
import uuid
import random
from datetime import datetime
from typing import Dict, Any

from protobuf_decoder.protobuf_decoder import Parser
import thunderFF_pb2
import br_evo_game

# ==================== CONFIG ====================
# MajorLogin host (loginbp) — Header "Host" real OB55 client pathay.
LOGIN_HOST = "loginbp.ppmainecoonghj.com"
# ✅ NEW: GetLoginData host (clientbp) — capture-e alada host dekha geche
CLIENT_HOST = "clientbp.ppmainecoonghj.com"

MAJORLOGIN_PATH = "MajorLogin"          # {server_url}MajorLogin
GETLOGIN_PATH = "GetLoginData"          # {base_url}/GetLoginData
PAYLOAD_LEGACY_ENV = "FF_LEGACY_PAYLOAD"  # =1 dile purono (protobuf-class) payload builder

# ✅ NEW: Latest OB55 X-GA-SV capture values (per-endpoint, ENV override kora jay)
X_GA_SV_MAJORLOGIN = os.environ.get("X_GA_SV_MAJORLOGIN", "1795616373")
X_GA_SV_GETLOGIN   = os.environ.get("X_GA_SV_GETLOGIN",   "1795616375")

# Response-e header prefix thakle protobuf kon offset theke shuru ta khujte koto byte scan korbe.
RESPONSE_OFFSET_SCAN = 128
RESPONSE_MIN_LEN = 40
OB55_HEADER_OFFSET = 64

# MajorLoginRes ban detection
BAN_STATUS_CODES = {2, 3, 8, 9, 10, 14, 15}
BAN_WORDS = ("ban", "suspend", "frozen", "terminat", "block", "disabled")

# ==================== INJECTED RUNTIME (app.py configure() call kore) ====================
_client = None
_headers: Dict[str, str] = {}
_aes_encrypt = None
_AES_KEY = b""
_AES_IV = b""
_report_fail = None
_version_config_invalidate = None
_parse_results = None


def configure(*, client, headers, aes_encrypt, aes_key, aes_iv,
              report_fail, version_config_invalidate, parse_results):
    global _client, _headers, _aes_encrypt, _AES_KEY, _AES_IV
    global _report_fail, _version_config_invalidate, _parse_results
    _client = client
    _headers = headers
    _aes_encrypt = aes_encrypt
    _AES_KEY = aes_key
    _AES_IV = aes_iv
    _report_fail = report_fail
    _version_config_invalidate = version_config_invalidate
    _parse_results = parse_results


def _require_configured():
    if _client is None or _aes_encrypt is None or _report_fail is None:
        raise RuntimeError("majors.configure() app.py theke call hoyni")


async def build_majorlogin_payload_legacy(open_id, access_token, platform, client_version, device_info):
    try:
        proto = thunderFF_pb2.MajorLoginReq()
        proto.event_time = str(datetime.now())[:-7]
        proto.game_name = "free fire"
        proto.platform_id = 1 if str(platform) in ["1", "4"] else int(platform)
        proto.client_version = client_version
        proto.client_version_code = "2019121229"
        
        # --- INJECTING PERSISTENT DYNAMIC DEVICE DATA ---
        proto.system_software = device_info.get("system_software", "Android OS 10 / API-29 (QQ3A.200805.001/135998ea76)")
        proto.system_hardware = device_info.get("brand", "Handheld")
        proto.device_type = device_info.get("model", "Handheld")
        proto.screen_width = int(device_info.get("screen_width", 1666))
        proto.screen_height = int(device_info.get("screen_height", 750))
        proto.screen_dpi = str(device_info.get("screen_dpi", "400"))
        proto.processor_details = device_info.get("processor_details", "ARM64 FP ASIMD AES | 2304 | 8")
        proto.memory = int(device_info.get("memory", 5602))
        proto.gpu_renderer = device_info.get("gpu_renderer", "Adreno (TM) 618")
        proto.unique_device_id = device_info.get("unique_device_id", "Google|725030d8-6585-4f55-bcca-a6df7e59935b")
        proto.client_ip = device_info.get("client_ip", "103.145.112.210")
        # ------------------------------------------------
        
        proto.telecom_operator = "Citycell"
        proto.network_operator_a = "Citycell"
        proto.network_type = "WIFI"
        proto.network_type_a = "WIFI"
        proto.cpu_type = 2
        proto.cpu_architecture = "64"
        proto.gpu_version = "OpenGL ES 3.2 V@415.0 (GIT@29668c6, I386ada412e, 1599643163) (Date:09/09/20)"
        proto.graphics_api = "OpenGLES2"
        proto.language = "en"
        proto.open_id = open_id
        proto.open_id_type = str(platform)
        proto.login_open_id_type = int(platform)
        proto.access_token = access_token
        proto.login_by = 2
        proto.platform_sdk_id = 1
        proto.origin_platform_type = str(platform)
        proto.primary_platform_type = str(platform)
        proto.reg_avatar = 1020000007  # ✅ FIXED: real client value (field 85 → reg_avatar_id)
        proto.channel_type = 3
        
        memory_available = proto.memory_available
        memory_available.version = 55
        memory_available.hidden_value = 81
        
        # ✅ Storage: real client capture থেকে হুবহু
        proto.external_storage_total = 107339
        proto.external_storage_available = 98183
        proto.internal_storage_total = 2477
        proto.internal_storage_available = 673
        proto.game_disk_storage_total = 98311   # ✅ FIXED: real client: 98311 (field 64)
        proto.game_disk_storage_available = 107339  # ✅ FIXED: real client: 107339 (field 65)
        proto.external_sdcard_total_storage = 98311   # ✅ FIXED: field 66
        proto.external_sdcard_avail_storage = 107339  # ✅ FIXED: field 67
        
        proto.library_path = "/data/app/com.dts.freefireth-cXks8_q21Wm61sLpm1Mwkw==/lib/arm64"
        proto.library_token = "b8e0cd5e295eee42f5860d3c86e483dd|/data/app/com.dts.freefireth-cXks8_q21Wm61sLpm1Mwkw==/base.apk"
        proto.client_using_version = "7428b253defc164018c604a1ebbfebdf"
        proto.supported_astc_bitset = 4095
        # analytics_detail (field 89) not sent by real OB55 client — omitted intentionally
        proto.loading_time = random.randint(5000, 9000)
        proto.release_channel = "android"
        proto.extra_info = "KqsHTwUcsotzm7T5wpHoa7zprR/0nb96MPMDflVhet3xaqMVtM9nR8cyff0bn0DL/AqN+M57YFwW+60+kUocBgoAwICMqslgRX9NHghmHqoVcF9O"
        proto.android_engine_init_flag = 111207
        proto.if_push = 1
        proto.is_vpn = 1  # ✅ FIXED: real client pathay 1 (WIFI/NAT behind router)
        
        payload = proto.SerializeToString()
        return await _aes_encrypt(payload, _AES_KEY, _AES_IV)
    except Exception:
        return None


# ==================== MAJORLOGIN PAYLOAD (REAL CLIENT LAYOUT) ====================
# Real game client-er MajorLogin packet-er field layout onujayi banano.
# Ager version-e 25 no. field ke message (memory_available) hishebe pathano hoto,
# kintu real client ekhane String (device name) pathay. Aro kichu field
# (85, 90, 91, 96, 102, 104-107) chilo na. Eigulo mismatch hoyei server
# BR_AUTH_ABNORMAL_GAME_CLIENT dicchilo.
def _pb_varint(n: int) -> bytes:
    n = int(n)
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def _pb_encode_fields(fields: Dict[int, Any]) -> bytes:
    """{field_no: int|str|bytes} -> protobuf bytes (field number order-e, real client-er moto)"""
    out = bytearray()
    for num in sorted(fields):
        val = fields[num]
        if val is None:
            continue
        if isinstance(val, bool):
            val = int(val)
        if isinstance(val, int):
            out += _pb_varint((num << 3) | 0) + _pb_varint(val)
        else:
            data = val if isinstance(val, (bytes, bytearray)) else str(val).encode("utf-8")
            out += _pb_varint((num << 3) | 2) + _pb_varint(len(data)) + bytes(data)
    return bytes(out)


# Device profile: real client theke paoa consistent hardware set (OS, GPU, CPU, storage ek sathe mele)
# ══════════════════════════════════════════════════════════════
# ✅ PER-UID DEVICE FINGERPRINT — প্রতিটা ID আলাদা ফোন মডেল
# একই UID সবসময় একই device পাবে (seed = UID hash)
# ══════════════════════════════════════════════════════════════
_DEVICE_POOL = [
    # (model, os_ver, api, build_id, screen_w, screen_h, dpi, cpu, ram, gpu_renderer, gpu_version, city)
    ("Xiaomi POCO X3",      "10", "29", "QQ3A.200805.001/135998ea76", 1066, 2400, "400", "ARM64 FP ASIMD AES | 2304 | 8", 5602,  "Adreno (TM) 618", "OpenGL ES 3.2 V@415.0 (GIT@29668c6, I386ada412e, 1599643163) (Date:09/09/20)", "Mymensingh"),
    ("Samsung Galaxy A32",  "11", "30", "RP1A.200720.012/A325FXXU5CVJ1",1080, 2400, "420", "ARM64 FP ASIMD AES | 2000 | 8", 5120,  "Mali-G57",        "OpenGL ES 3.2 v1.r32p1-01eac0.37c1571c4ca7e4be7e8f5a5c7e8aba5a", "Dhaka"),
    ("Samsung Galaxy A52",  "11", "30", "RP1A.200720.012/A525FXXU4CVJ2",1080, 2400, "420", "ARM64 FP ASIMD AES | 2000 | 8", 6144,  "Adreno (TM) 618", "OpenGL ES 3.2 V@415.0 (GIT@29668c6, I386ada412e, 1599643163) (Date:09/09/20)", "Chittagong"),
    ("Redmi Note 10",       "11", "30", "RKQ1.200826.002/V12.0.4.0",   1080, 2400, "395", "ARM64 FP ASIMD AES | 2000 | 8", 5120,  "Adreno (TM) 612", "OpenGL ES 3.2 V@0502.0 (GIT@a21ad, I60c1e, 1611770046) (Date:01/27/21)", "Sylhet"),
    ("Redmi 9",             "10", "29", "QKQ1.191117.002/V11.0.5.0",    720, 1600, "269", "ARM64 FP ASIMD AES | 2000 | 8", 4096,  "Mali-G52-MC2",    "OpenGL ES 3.2 v1.r19p0-01rel0.6d1f6b4e72c3c2de76df1f5b0", "Rajshahi"),
    ("Realme C35",          "11", "30", "RP1A.200720.011/RMX3511PU_11", 1080, 2408, "400", "ARM64 FP ASIMD AES | 1800 | 8", 4096,  "Mali-G57 MC2",    "OpenGL ES 3.2 v1.r32p1-01eac0.37c1571c4ca7e4be7e8f5a5c7e8aba5a", "Khulna"),
    ("Vivo Y21",            "11", "30", "RP1A.200720.012/V210_A_6.35.0", 720, 1600, "270", "ARM64 FP ASIMD AES | 1800 | 8", 3072,  "PowerVR GE8320",  "OpenGL ES 3.2 build 1.13@5776728", "Barisal"),
    ("OPPO A57",            "11", "30", "RP1A.200720.011/CPH2387PU_11",  720, 1612, "269", "ARM64 FP ASIMD AES | 1800 | 8", 3072,  "PowerVR GE8320",  "OpenGL ES 3.2 build 1.13@5776728", "Comilla"),
    ("Tecno Spark 8",       "11", "30", "RP1A.200720.011/TECNO-KG6j",    720, 1600, "270", "ARM64 FP ASIMD AES | 1600 | 8", 2048,  "Mali-G52-MC2",    "OpenGL ES 3.2 v1.r19p0-01rel0.6d1f6b4e72c3c2de76df1f5b0", "Rangpur"),
    ("Xiaomi Redmi Note 11","11", "30", "RP1A.200720.011/V13.0.1.0",    1080, 2400, "395", "ARM64 FP ASIMD AES | 2000 | 8", 4096,  "Adreno (TM) 610", "OpenGL ES 3.2 V@0502.0 (GIT@a21ad, I60c1e, 1611770046) (Date:01/27/21)", "Gazipur"),
    ("Samsung Galaxy M32",  "11", "30", "RP1A.200720.012/M325FXXU3CVJ1",1080, 2400, "420", "ARM64 FP ASIMD AES | 2000 | 8", 6144,  "Mali-G57",        "OpenGL ES 3.2 v1.r32p1-01eac0.37c1571c4ca7e4be7e8f5a5c7e8aba5a", "Narayanganj"),
    ("Infinix Hot 11",      "11", "30", "RP1A.200720.011/H6116V2P1",    720, 1600, "270", "ARM64 FP ASIMD AES | 1600 | 8", 2048,  "Mali-G52-MC2",    "OpenGL ES 3.2 v1.r19p0-01rel0.6d1f6b4e72c3c2de76df1f5b0", "Jessore"),
]

_uid_device_cache: dict = {}

def _get_device_for_uid(uid: str) -> dict:
    """UID hash দিয়ে consistent কিন্তু unique device profile তৈরি করে"""
    if uid in _uid_device_cache:
        return _uid_device_cache[uid]
    rng = random.Random(int(uid) if uid.isdigit() else hash(uid))
    d = rng.choice(_DEVICE_POOL)
    model, os_ver, api, build_id, sw, sh, dpi, cpu, ram, gpu_r, gpu_v, city = d
    # Storage — realistic variation (device অনুযায়ী)
    ext_total  = rng.randint(60000, 120000)
    ext_avail  = rng.randint(int(ext_total * 0.6), int(ext_total * 0.9))
    int_total  = rng.randint(2000, 4000)
    int_avail  = rng.randint(400, 800)
    apk_suffix = ''.join(rng.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-', k=20))
    lib_path   = f"/data/app/com.dts.freefireth-{apk_suffix}==/lib/arm64"
    lib_md5    = ''.join(rng.choices('0123456789abcdef', k=32))
    lib_token  = f"{lib_md5}|/data/app/com.dts.freefireth-{apk_suffix}==/base.apk"
    profile = {
        8:  f"Android OS {os_ver} / API-{api} ({build_id})",
        12: sw,
        13: sh,
        14: str(dpi),
        15: cpu,
        16: ram,
        17: gpu_r,
        18: gpu_v,
        25: model,
        60: ext_total,
        61: ext_avail,
        62: int_total,
        63: int_avail,
        64: ext_total - rng.randint(100, 500),
        65: ext_avail,
        66: ext_total,
        67: ext_avail,
        74: lib_path,
        77: lib_token,
        90: city,
    }
    _uid_device_cache[uid] = profile
    return profile


REAL_CLIENT_PROFILE = {
    # ✅ UPDATED: Real OB55 client capture থেকে (loginbp.ppmainecoonghj.com)
    8:  "Android OS 10 / API-29 (QQ3A.200805.001/135998ea76)",  # field 8: system_software
    9:  "Handheld",                                              # field 9: system_hardware
    12: 1666,                                                    # field 12: screen_width
    13: 750,                                                     # field 13: screen_height
    14: "400",                                                   # field 14: screen_dpi
    15: "ARM64 FP ASIMD AES | 2304 | 8",                        # field 15: processor_details
    16: 5602,                                                    # field 16: memory
    17: "Adreno (TM) 618",                                      # field 17: gpu_renderer
    18: "OpenGL ES 3.2 V@415.0 (GIT@29668c6, I386ada412e, 1599643163) (Date:09/09/20)",  # field 18: gpu_version
    24: "Handheld",                                             # field 24: device_type
    25: "Xiaomi POCO X3",                                       # field 25: device_model (real client value)
    57: "7428b253defc164018c604a1ebbfebdf",                     # field 57: client_using_version (signature_md5)
    # ✅ Storage fields — real client capture থেকে হুবহু
    60: 107339,   # external_storage_total
    61: 98183,    # external_storage_available
    62: 2477,     # internal_storage_total
    63: 673,      # internal_storage_available
    64: 98311,    # game_disk_storage_total → field 64 (real client: 98311)
    65: 107339,   # game_disk_storage_available → field 65 (real client: 107339)
    66: 98311,    # external_sdcard_total_storage
    67: 107339,   # external_sdcard_avail_storage
    74: "/data/app/com.dts.freefireth-cXks8_q21Wm61sLpm1Mwkw==/lib/arm64",  # library_path
    77: "b8e0cd5e295eee42f5860d3c86e483dd|/data/app/com.dts.freefireth-cXks8_q21Wm61sLpm1Mwkw==/base.apk",  # library_token
    90: "Mymensingh",                                           # field 90: city/region string
    91: "H",                                                    # field 91: (real client value)
    94: "KqsHTwUcsotzm7T5wpHoa7zprR/0nb96MPMDflVhet3xaqMVtM9nR8cyff0bn0DL/AqN+M57YFwW+60+kUocBgoAwICMqslgRX9NHghmHqoVcF9O",  # extra_info
    96: '{"cur_rate":[50,30,60,90,120],"support_etc2":false}',  # field 96: graphics config
    # field 102: nested message {8: 3602980918476556118} — encoded in _build_majorlogin_raw
    104: 25589,   # field 104: android_engine_init_flag → real client: 25589
    105: 1,       # ✅ ADDED: field 105 — real client pathay, আগে ছিল না
    106: "https://dl-bs.ggpolarbear.com/live/ABHotUpdates/|https://core-bs.ggpolarbear.com/live/ABHotUpdates/|a4332cb1c1a84e51dd77441e4856ed5a",  # field 106
    107: "1.9393e7b8e53e8aeb",  # field 107
}


def _build_majorlogin_raw(open_id, access_token, platform, client_version, device_info) -> bytes:
    plat = str(platform)
    f: Dict[int, Any] = dict(REAL_CLIENT_PROFILE)
    f.update({
        # ✅ Dynamic fields — প্রতি login-এ পরিবর্তিত হয়
        3:  str(datetime.now())[:-7],                          # event_time
        4:  "free fire",                                        # game_name
        5:  1 if plat in ("1", "4") else int(platform),        # platform_id
        7:  client_version,                                     # client_version
        11: "WIFI",                                             # network_type
        19: (device_info or {}).get("unique_device_id") or f"Google|{uuid.uuid4()}",  # unique_device_id
        20: (device_info or {}).get("client_ip") or "27.123.253.203",  # ✅ UPDATED: real client IP
        21: "en",                                               # language
        22: open_id,                                            # open_id
        23: plat,                                               # open_id_type
        29: access_token,                                       # access_token
        30: 1,                                                  # platform_sdk_id
        42: "WIFI",                                             # network_type_a
        73: 2,                                                  # cpu_type
        76: 1,                                                  # login_by
        78: 3,                                                  # channel_type (real client: 3)
        79: 2,                                                  # login_open_id_type (real client: 2)
        81: "64",                                               # cpu_architecture
        83: "2019121229",                                       # client_version_code
        85: 3,                                                  # reg_avatar → field 85 (real: 3)
        86: "OpenGLES2",                                        # graphics_api
        87: 4095,                                               # supported_astc_bitset
        88: int(platform),                                      # platform (real client: 4)
        92: random.randint(5000, 9000),                         # loading_time (jitter)
        93: "android",                                          # release_channel
        95: 111207,                                             # android_engine_init_flag (real: 111207)
        97: 1,                                                  # if_push
        98: 1,                                                  # is_vpn → real client: 1 (NAT/WIFI)
        99: plat,                                               # origin_platform_type
        100: plat,                                              # primary_platform_type
        # field 102: nested message { field_8: uint64 } — must be raw bytes, NOT a string
        102: _pb_encode_fields({8: 3602980918476556118}),       # ✅ real client value হুবহু
        # field 105 → REAL_CLIENT_PROFILE-এ আছে (value: 1), override করা হচ্ছে না
    })
    return _pb_encode_fields(f)


async def build_majorlogin_payload(open_id, access_token, platform, client_version, device_info):
    _require_configured()
    try:
        if os.environ.get(PAYLOAD_LEGACY_ENV) == "1":
            return await build_majorlogin_payload_legacy(open_id, access_token, platform, client_version, device_info)
        payload = _build_majorlogin_raw(open_id, access_token, platform, client_version, device_info)
        return await _aes_encrypt(payload, _AES_KEY, _AES_IV)
    except Exception as e:
        _report_fail(None, "MajorLogin payload build exception", repr(e)[:200])
        return None


# MajorLogin রেসপন্সের field 16 (stronghold url) — thunderFF_pb2-তে নেই, তাই raw থেকে নিয়ে এখানে রাখা হয়
_STRONGHOLD_BY_ACC: Dict[str, str] = {}

async def send_majorlogin(data, release_version, server_url):
    _require_configured()
    try:
        url = f"{server_url}{MAJORLOGIN_PATH}"
        req_headers = _headers.copy()
        req_headers["ReleaseVersion"] = release_version
        req_headers["Host"] = LOGIN_HOST                    # ✅ real client: loginbp.ppmainecoonghj.com
        req_headers["X-GA-SV"] = X_GA_SV_MAJORLOGIN         # ✅ NEW: per-endpoint X-GA-SV
        # ✅ Direct connection — free proxy 400 error দেয়, তাই proxy ছাড়াই login
        response = await _client.post(url, headers=req_headers, data=data)
        if response.status_code != 200:
            _report_fail(None, f"MajorLogin HTTP {response.status_code}", f"url={url} body={response.text[:150]}")
            return None
        response_content = response.content
        if len(response_content) < RESPONSE_MIN_LEN:
            _report_fail(None, "MajorLogin response too short", f"{len(response_content)} bytes: {response_content[:60]!r}")
            return None

        try:
            _acc_s, _sh = br_evo_game.extract_majorlogin_extras(response_content)
            if _acc_s:
                _STRONGHOLD_BY_ACC[_acc_s] = _sh or ""
        except Exception:
            pass

        # 1. Direct parse
        def _check_majorlogin_ban(proto):
            """MajorLoginRes-এ ban/suspend status code আছে কিনা চেক করে"""
            # status field: 0=ok, 2=banned, 3=suspended, 8=frozen — Garena specific
            _BAN_STATUS = BAN_STATUS_CODES
            status = getattr(proto, 'status', None) or getattr(proto, 'error_code', None)
            if status in _BAN_STATUS:
                return True
            # error_msg field চেক
            _BAN_WORDS = BAN_WORDS
            msg = str(getattr(proto, 'error_msg', '') or getattr(proto, 'msg', '') or '').lower()
            return any(w in msg for w in _BAN_WORDS)

        res_proto = thunderFF_pb2.MajorLoginRes()
        try:
            res_proto.ParseFromString(response_content)
            if _check_majorlogin_ban(res_proto):
                _report_fail(None, "[BANNED] MajorLoginRes ban status detected", f"status={getattr(res_proto,'status',None)}")
                return "BANNED"
            if res_proto.region and res_proto.token:
                return res_proto
        except Exception:
            pass

        # 2. OB55 64-byte header offset check (response capture-e header 64 byte confirmed)
        if len(response_content) > OB55_HEADER_OFFSET:
            try:
                res_proto = thunderFF_pb2.MajorLoginRes()
                res_proto.ParseFromString(response_content[OB55_HEADER_OFFSET:])
                if _check_majorlogin_ban(res_proto):
                    return "BANNED"
                if res_proto.region and res_proto.token:
                    return res_proto
            except Exception:
                pass

        # 3. Dynamic offset search for OB55 compatibility
        for offset in range(min(RESPONSE_OFFSET_SCAN, len(response_content))):
            try:
                candidate = thunderFF_pb2.MajorLoginRes()
                candidate.ParseFromString(response_content[offset:])
                if _check_majorlogin_ban(candidate):
                    return "BANNED"
                if candidate.region and candidate.token:
                    return candidate
            except Exception:
                pass

        res_proto = thunderFF_pb2.MajorLoginRes()
        res_proto.ParseFromString(response_content)
        if not res_proto.token:
            _report_fail(None, "MajorLogin token khali (version/payload mismatch hote pare)", f"{len(response_content)} bytes")
            # ✅ FIX: token নেই মানে version mismatch — cache clear করো
            _version_config_invalidate()
            return None
        return res_proto
    except Exception as e:
        _e_str = repr(e)
        _report_fail(None, "MajorLogin exception", _e_str[:200])
        # ✅ FIX: DecodeError = server নতুন OB version দিচ্ছে, আমরা পুরনো parse করছি
        # Cache clear করলে পরের retry-তে নতুন version fetch হবে → সব bot ঠিক হবে
        if "DecodeError" in _e_str or "Error parsing message" in _e_str:
            _version_config_invalidate()
        return None

async def send_getlogin(data, base_url, token, release_version):
    _require_configured()
    try:
        # ✅ NEW: GetLoginData host = clientbp (not loginbp). force replace.
        # base_url ver.php theke ashe, kintu real OB55 client clientbp host use kore.
        _url = f"{base_url.rstrip('/')}/{GETLOGIN_PATH}"
        _url = _url.replace("loginbp.", "clientbp.")  # force clientbp host

        req_headers = _headers.copy()
        req_headers["ReleaseVersion"] = release_version
        req_headers['Authorization'] = f"Bearer {token}"
        req_headers['Host'] = CLIENT_HOST                # ✅ real client: clientbp.ppmainecoonghj.com
        req_headers['X-GA-SV'] = X_GA_SV_GETLOGIN        # ✅ NEW: GetLoginData-er X-GA-SV (alada value)
        # ✅ Direct connection — proxy ছাড়াই GetLoginData
        response = await _client.post(_url, headers=req_headers, data=data)
        if response.status_code != 200:
            _report_fail(None, f"GetLoginData HTTP {response.status_code}", f"url={_url} body={response.text[:150]}")
            return None
        response_content = response.content

        res_proto = thunderFF_pb2.GetLoginDataRes()
        parsed_successfully = False
        try:
            res_proto.ParseFromString(response_content)
            if res_proto.functional_addrs or res_proto.informational_addrs:
                parsed_successfully = True
        except Exception:
            pass

        if not parsed_successfully:
            for offset in range(min(RESPONSE_OFFSET_SCAN, len(response_content))):
                try:
                    candidate = thunderFF_pb2.GetLoginDataRes()
                    candidate.ParseFromString(response_content[offset:])
                    if candidate.functional_addrs or candidate.informational_addrs:
                        res_proto = candidate
                        break
                except Exception:
                    pass

        dict_res = {}
        try:
            parsed = Parser().parse(response_content.hex())
            dict_res = await _parse_results(parsed)
        except Exception:
            pass

        return res_proto, dict_res
    except Exception as e:
        _report_fail(None, "GetLoginData exception", repr(e)[:200])
        return None