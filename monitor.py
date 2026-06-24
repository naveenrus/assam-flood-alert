from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import urllib3
import pdfplumber
import re
import os
import smtplib
from email.mime.text import MIMEText

urllib3.disable_warnings()

session = requests.Session()

yesterday = (
    datetime.now() - timedelta(days=1)
).strftime("%Y-%m-%d")


# ====================================================
# DOWNLOAD REPORT
# ====================================================

def download_report(report_type, output_file):

    page = session.get(
        f"https://sdrf.assam.gov.in/dfr/download?type={report_type}",
        verify=False,
        timeout=60
    )

    soup = BeautifulSoup(page.text, "html.parser")

    token = soup.find(
        "input",
        {"name": "_token"}
    )["value"]

    payload = {
        "_token": token,
        "type": report_type,
        "date": yesterday
    }

    pdf = session.post(
        "https://sdrf.assam.gov.in/dfr/download",
        data=payload,
        verify=False,
        timeout=120
    )

    with open(output_file, "wb") as f:
        f.write(pdf.content)

    print(f"Downloaded: {output_file}")


# ====================================================
# PDF TO TEXT
# ====================================================

def pdf_to_text(pdf_file):

    text = ""

    with pdfplumber.open(pdf_file) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    return text


# ====================================================
# FLOOD INFO
# ====================================================
def extract_flood_info(text):

    result = {}

    m = re.search(
        r'Assam Flood Report as on\s+(\d{2}-\d{2}-\d{4})',
        text
    )

    result["date"] = m.group(1) if m else "NA"

    m = re.search(
        r'Name of Affected Districts\s*(.*?)\s*No\. Of',
        text,
        re.DOTALL | re.IGNORECASE
    )

    if m:

        districts = m.group(1)

        districts = districts.replace(
            "Affected Districts",
            ""
        )

        districts = districts.replace(
            "Affected",
            ""
        )

        districts = districts.strip()

        districts = re.sub(
            r'^\d+\s*',
            '',
            districts
        )

        result["districts"] = districts

        district_list = [
            x.strip()
            for x in districts.split(",")
            if x.strip()
        ]

        result["district_count"] = len(
            district_list
        )

    else:

        result["districts"] = "NA"
        result["district_count"] = 0

    result["population"] = "NA"
    result["crop_area"] = "NA"

    m = re.search(
        r'Total\s+\d+\s+\d+\s+\d+\s+(\d+)\s+([\d.]+)',
        text
    )

    if m:

        result["population"] = m.group(1)
        result["crop_area"] = m.group(2)

    m = re.search(
        r'Rivers flowing above danger level\s*(.*)',
        text,
        re.IGNORECASE
    )

    result["river"] = m.group(1).strip() if m else "NA"

    result["relief_camps"] = "NA"

    return result
# ====================================================
# RAINFALL INFO
# ====================================================

def extract_rainfall_info(text):

    stations = []

    current_district = None

    lines = text.split("\n")

    station_district_fix = {
        "BARPETA_ARG": "BARPETA",
        "BAJALI_UNIVERSITY": "BARPETA",
        "SRIJANGRAM": "BONGAIGAON",
        "LAKHIPUR": "CACHAR",
        "SONARI": "CHARAIDEO",
        "SONARI_AEGCL": "CHARAIDEO",
        "MANGALDAI": "DARRANG",
        "SILAPATHAR_SCIENCE_COLLEGE": "DHEMAJI",
        "DHUBRI_KVK": "DHUBRI",
        "GAURIPUR_AEGCL": "DHUBRI",
        "BN_COLLEGE": "DIBRUGARH",
        "BCPL_DIBRUGARH": "DIBRUGARH",
        "DC_OFC_DIBRUGARH": "DIBRUGARH",
        "WRD": "DIBRUGARH",
        "UMRANGSHU": "DIMA_HASAO",
        "DUDHNOI": "GOALPARA",
        "BOKAKHAT": "GOLAGHAT",
        "CNB_COLLAGE_BOKAKHAT": "GOLAGHAT",
        "MATIJURI": "HAILAKANDI",
        "PANCHGRAM_AEGCL": "HAILAKANDI",
        "LUMDING": "HOJAI",
        "TEOK": "JORHAT",
        "MARIYANI_AEGCL": "JORHAT",
        "SALAKATI_AEGCL": "KOKRAJHAR",
        "CHOULDHUAGHAT": "LAKHIMPUR",
        "MAJULI": "MAJULI",
        "DHARAMTUL": "MARIGAON",
        "KAMPUR": "NAGAON",
        "TIHU": "NALBARI",
        "NALBARI_KVK": "NALBARI",
        "SIVSAGAR_AEGCL": "SIVASAGAR",
        "GHORAMARA_AEGCL": "SONITPUR",
        "MUSHALPUR": "TAMULPUR",
        "MARGHERITA": "TINSUKIA",
        "NTPS_APDCL": "TINSUKIA",
        "RUPAI_AEGCL": "TINSUKIA",
        "ROWTA_AEGCL": "UDALGURI",
        "TAMULPUR": "TAMULPUR",
        "TIHU": "NALBARI",
        "TAMULPUR": "TAMULPUR",
        "MUSHALPUR": "TAMULPUR"
    }

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # Format: CACHAR LAKHIPUR 52
        m = re.match(
            r'^([A-Z_()]+)\s+([A-Z_()]+)\s+(\d+(?:\.\d+)?)$',
            line
        )

        if m:

            district = m.group(1)
            location = m.group(2)
            rain = float(m.group(3))

            if rain <= 300:

                stations.append(
                    (
                        district,
                        location,
                        rain
                    )
                )

            continue

        # District only line
        if re.match(
            r'^[A-Z_()]+$',
            line
        ):

            current_district = line
            continue

        # Format: MUSHALPUR 93
        m = re.match(
            r'^([A-Z_()]+)\s+(\d+(?:\.\d+)?)$',
            line
        )

        if m and current_district:

            location = m.group(1)
            rain = float(m.group(2))

            if rain <= 300:

                stations.append(
                    (
                        current_district,
                        location,
                        rain
                    )
                )

    # Fix district names

    fixed_stations = []

    for district, location, rain in stations:

        district = station_district_fix.get(
            location,
            district
        )

        fixed_stations.append(
            (
                district,
                location,
                rain
            )
        )

    stations = fixed_stations

    # Remove duplicates

    stations = list(
        dict.fromkeys(stations)
    )

    stations.sort(
        key=lambda x: x[2],
        reverse=True
    )

    highest = stations[0] if stations else None

    heavy = [
        x for x in stations
        if x[2] >= 64.5
    ]

    top5 = stations[:5]

    return highest, heavy, top5, stations

# ====================================================
# RISK LEVEL
# ====================================================

# ====================================================
# MAIN
# ====================================================

flood_pdf = f"Flood_Report_{yesterday}.pdf"
rain_pdf = f"Rainfall_Report_{yesterday}.pdf"

download_report(
    "flood",
    flood_pdf
)

download_report(
    "rainfall",
    rain_pdf
)

flood_text = pdf_to_text(
    flood_pdf
)

rain_text = pdf_to_text(
    rain_pdf
)

with open(
    "rainfall_text.txt",
    "w",
    encoding="utf-8"
) as f:

    f.write(rain_text)

flood_info = extract_flood_info(
    flood_text
)

# DUPLICATE CHECK


LAST_REPORT_FILE = "data/last_report_date.txt"

current_report_date = flood_info.get(
    "date",
    "NA"
)

if os.path.exists(LAST_REPORT_FILE):

    with open(
        LAST_REPORT_FILE,
        "r"
    ) as f:

        last_report_date = f.read().strip()

    if last_report_date == current_report_date:

        print(
            f"Report {current_report_date} already processed."
        )

        raise SystemExit

highest, heavy, top5, stations = extract_rainfall_info(
    rain_text
)

print("\n")
print("=" * 70)
print("🚨 ASSAM FLOODWATCH-AI DAILY ALERT")
print("=" * 70)

# ====================================================
# REPORT DATE
# ====================================================

print("\n🆕 REPORT DATE")

print(
    flood_info.get(
        "date",
        "NA"
    )
)

# ====================================================
# EXECUTIVE SUMMARY
# ====================================================

print("\n⚡ EXECUTIVE SUMMARY")
print("-" * 40)


print(
    f"Affected Districts  : {flood_info.get('district_count',0)}"
)

print(
    f"Population Affected : {flood_info.get('population','NA')}"
)

if highest:

    print(
        f"Highest Rainfall    : {highest[1]} ({highest[2]} mm) - {highest[0]}"
    )

print(
    f"River Status        : {flood_info.get('river','NA')}"
)

# ====================================================
# FLOOD STATUS
# ====================================================

print("\n🌊 FLOOD STATUS")
print("-" * 40)

print(
    flood_info.get(
        "districts",
        "NA"
    )
)

print(
    f"\nPopulation Affected : {flood_info.get('population','NA')}"
)

print(
    f"Crop Area Affected  : {flood_info.get('crop_area','NA')} ha"
)

print(
    f"Relief Camps        : {flood_info.get('relief_camps','NA')}"
)

print(
    f"River Status        : {flood_info.get('river','NA')}"
)

# ====================================================
# FLOOD DISTRICT RAINFALL STATUS
# ====================================================

print("\n⚠ FLOOD DISTRICT RAINFALL STATUS")
print("-" * 90)

affected = [
    x.strip().upper()
    for x in flood_info["districts"].split(",")
]

affected_stations = [
    (district, location, rain)
    for district, location, rain in stations
    if district and district.upper() in affected
]

affected_stations.sort(
    key=lambda x: x[2],
    reverse=True
)

if affected_stations:

    print(
        f"{'District':20s} {'Location':35s} {'Rainfall(mm)':>12s}"
    )

    print("-" * 90)

    for district, location, rain in affected_stations:

        print(
            f"{district:20s} {location:35s} {rain:12.1f}"
        )

else:

    print(
        "No rainfall stations found in affected districts"
    )

# ====================================================
# HEAVY RAINFALL STATIONS
# ====================================================

print("\n🌧 HEAVY RAINFALL STATIONS")
print("-" * 90)

if heavy:

    print(
        f"{'District':20s} {'Location':35s} {'Rainfall(mm)':>12s}"
    )

    print("-" * 90)

    for district, location, rain in heavy:

        print(
            f"{district:20s} {location:35s} {rain:12.1f}"
        )

else:

    print(
        "No Heavy Rainfall Reported"
    )

# ====================================================
# FLOOD SUMMARY
# ====================================================

print("\n📊 FLOOD SUMMARY")
print("-" * 40)

print(
    f"Flood Affected Districts : {flood_info.get('district_count',0)}"
)

print(
    f"Population Affected      : {flood_info.get('population','NA')}"
)

print(
    f"Crop Area Affected (ha)  : {flood_info.get('crop_area','NA')}"
)

if highest:

    print(
        f"Highest Rainfall         : {highest[1]} ({highest[2]} mm)"
    )

# ====================================================
# RECOMMENDED ACTIONS
# ====================================================

print("\n📌 RECOMMENDED ACTIONS")
print("-" * 40)

print("✓ Monitor flood affected districts")
print("✓ Monitor river gauge levels")
print("✓ Monitor heavy rainfall stations")
print("✓ Keep local response teams informed")

# ====================================================
# FOOTER
# ====================================================

print("\n")
print("------------------------------------------------------------")
print("FLOODWATCH-AI")
print("Automated Assam Flood & Rainfall Monitoring System")
print("")
print("Developed by Nani")
print("M.Tech - Spatial Information Technology")
print("JNTUH Hyderabad")
print(
    f"Generated On       : {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
)
print("------------------------------------------------------------")
email_body = f"""
ASSAM FLOODWATCH-DAILY ALERT

Report Date:
{flood_info.get('date','NA')}

Affected Districts:
{flood_info.get('districts','NA')}

Population Affected:
{flood_info.get('population','NA')}

Crop Area Affected:
{flood_info.get('crop_area','NA')} ha

River Status:
{flood_info.get('river','NA')}

Highest Rainfall:
{highest[1]} ({highest[2]} mm) - {highest[0]}

Generated By:
FLOODWATCH-AI
Developed by Nani
JNTUH Hyderabad
"""

EMAIL_USER = "bussarinaveen18@gmail.com"
EMAIL_PASS = "lkty eqzy yywh mklr"

EMAIL_TO = [
    "bussarinaveen18@gmail.com"
]

msg = MIMEText(email_body)

msg["Subject"] = (
    f"🚨 Assam Flood Alert | {current_report_date}"
)

msg["From"] = EMAIL_USER
msg["To"] = ", ".join(EMAIL_TO)

with smtplib.SMTP_SSL(
    "smtp.gmail.com",
    465
) as server:

    server.login(
        EMAIL_USER,
        EMAIL_PASS
    )

    server.sendmail(
        EMAIL_USER,
        EMAIL_TO,
        msg.as_string()
    )

print("Email Sent Successfully")
