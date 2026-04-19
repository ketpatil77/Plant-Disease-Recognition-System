from __future__ import annotations

import re
from datetime import datetime

from .model import BACKGROUND_CLASS, IDX_TO_CLASSES

MARATHI_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")

CROP_TRANSLATIONS = {
    "Apple": "सफरचंद",
    "Blueberry": "ब्लूबेरी",
    "Cherry": "चेरी",
    "Corn": "मका",
    "Grape": "द्राक्ष",
    "Orange": "संत्रे",
    "Peach": "पीच",
    "Pepper bell": "ढोबळी मिरची",
    "Potato": "बटाटा",
    "Raspberry": "रास्पबेरी",
    "Soybean": "सोयाबीन",
    "Squash": "भोपळा",
    "Strawberry": "स्ट्रॉबेरी",
    "Tomato": "टोमॅटो",
    "Upload": "अपलोड",
    "Unknown": "अज्ञात",
}

DISEASE_TRANSLATIONS = {
    "Apple scab": {
        "name": "स्कॅब रोग",
        "cause": "ही बुरशीजन्य समस्या असून थंड व ओलसर हवामानात वेगाने वाढते.",
        "cure": "प्रतिरोधक वाण वापरा, संक्रमित पाने काढा आणि योग्य बुरशीनाशकाची फवारणी करा.",
    },
    "Black rot": {
        "name": "काळा कुज रोग",
        "cause": "हा रोग बुरशीमुळे होतो आणि पानांवर तसेच फळांवर काळे डाग निर्माण करतो.",
        "cure": "संक्रमित भाग छाटून नष्ट करा आणि हंगामात बुरशीनाशकाचा वापर करा.",
    },
    "Cedar apple rust": {
        "name": "सीडर सफरचंद गंज",
        "cause": "हा बुरशीजन्य रोग असून जवळील जुनिपर झाडांमुळे संक्रमण वाढते.",
        "cure": "जवळील पर्यायी यजमान काढा आणि प्रतिरोधक वाणांसोबत बुरशीनाशक वापरा.",
    },
    "Powdery mildew": {
        "name": "भुरी रोग",
        "cause": "पानांच्या पृष्ठभागावर पांढरट भुकटीसारखी वाढ दिसते; हा बुरशीजन्य रोग आहे.",
        "cure": "सल्फर-आधारित किंवा शिफारसीय बुरशीनाशक वापरा आणि हवेशीरपणा वाढवा.",
    },
    "Cercospora leaf spot Gray leaf spot": {
        "name": "करडा पर्णडाग / सर्कोस्पोरा डाग",
        "cause": "सर्कोस्पोरा बुरशीमुळे पानांवर लांबट करडे डाग दिसतात.",
        "cure": "प्रतिरोधक संकरित वाण वापरा आणि लवकर बुरशीनाशक फवारणी करा.",
    },
    "Common rust": {
        "name": "सामान्य गंज",
        "cause": "गंजासारखे तपकिरी-तांबूस उठाव पानांवर दिसतात; हा बुरशीजन्य रोग आहे.",
        "cure": "प्रतिरोधक वाण वापरा आणि गरजेनुसार बुरशीनाशक फवारणी करा.",
    },
    "Northern Leaf Blight": {
        "name": "उत्तरी पान करपा",
        "cause": "लांबट करपल्यासारखे डाग निर्माण करणारा हा बुरशीजन्य रोग आहे.",
        "cure": "संक्रमण वाढण्याआधी योग्य बुरशीनाशक वापरा आणि प्रतिरोधक वाण निवडा.",
    },
    "Esca (Black Measles)": {
        "name": "एस्का / काळे डाग रोग",
        "cause": "हा द्राक्षातील जटिल बुरशीजन्य रोग असून लाकूड आणि पानांना हानी पोहोचवतो.",
        "cure": "संक्रमित फांद्या काढा, जखमा टाळा आणि स्वच्छ बाग व्यवस्थापन ठेवा.",
    },
    "Leaf blight (Isariopsis Leaf Spot)": {
        "name": "पर्ण करपा / पर्णडाग",
        "cause": "पानांवर तपकिरी करपल्यासारखे डाग निर्माण करणारा बुरशीजन्य रोग.",
        "cure": "वेळीच बुरशीनाशक फवारणी करा आणि बागेची स्वच्छता राखा.",
    },
    "Haunglongbing (Citrus greening)": {
        "name": "ह्वांगलाँगबिंग / सिट्रस ग्रीनिंग",
        "cause": "हा जीवाणूजन्य रोग असून सायलिड कीटकांद्वारे पसरतो.",
        "cure": "सायलिडचे नियंत्रण करा आणि जास्त संक्रमित झाडे काढून टाका.",
    },
    "Bacterial spot": {
        "name": "जीवाणूजन्य डाग",
        "cause": "पानांवर आणि फळांवर सूक्ष्म डाग निर्माण करणारा हा जीवाणूजन्य रोग आहे.",
        "cure": "तांब्याधारित जीवाणूनाशक वापरा, स्वच्छता पाळा आणि प्रतिरोधक वाण वापरा.",
    },
    "Early blight": {
        "name": "लवकर करपा",
        "cause": "हा बुरशीजन्य रोग असून जुन्या पानांवर गोल वर्तुळाकार डाग दिसतात.",
        "cure": "संक्रमित पाने काढा, पीक फेरपालट ठेवा आणि शिफारसीय बुरशीनाशक वापरा.",
    },
    "Late blight": {
        "name": "उशीरा करपा",
        "cause": "आर्द्र हवामानात झपाट्याने पसरणारा गंभीर करपा रोग.",
        "cure": "त्वरित प्रणालीगत बुरशीनाशक वापरा आणि संक्रमित भाग वेगळा करा.",
    },
    "Leaf Mold": {
        "name": "पान बुरशी",
        "cause": "जास्त आर्द्रतेमुळे पानांच्या खालच्या बाजूला बुरशीची वाढ दिसते.",
        "cure": "हरितगृह किंवा शेतातील हवेशीरपणा वाढवा आणि योग्य बुरशीनाशक वापरा.",
    },
    "Septoria leaf spot": {
        "name": "सेप्टोरिया पर्णडाग",
        "cause": "छोटे गोल डाग निर्माण करणारा हा बुरशीजन्य रोग आहे.",
        "cure": "संक्रमित पाने काढून टाका आणि सुरुवातीच्या अवस्थेत बुरशीनाशक फवारणी करा.",
    },
    "Spider mites Two-spotted spider mite": {
        "name": "दोन ठिपक्यांचा कोळी किड",
        "cause": "पानांच्या खालच्या बाजूस कोळी किड वाढून रस शोषतो.",
        "cure": "विशिष्ट अॅकारिसाइड किंवा नीम-आधारित उपाय वापरा आणि सकाळी तपासणी करा.",
    },
    "Target Spot": {
        "name": "टार्गेट स्पॉट",
        "cause": "लक्ष्यासारखे वर्तुळाकार डाग निर्माण करणारा हा बुरशीजन्य रोग आहे.",
        "cure": "लवकर बुरशीनाशक वापरा, गर्दी कमी करा आणि हवेशीरपणा वाढवा.",
    },
    "Tomato Yellow Leaf Curl Virus": {
        "name": "पिवळे पान वाकडेपणा विषाणू",
        "cause": "हा विषाणू पांढरी माशीमार्फत पसरतो आणि पाने वाकडी व पिवळी होतात.",
        "cure": "वाहक कीटकांचे नियंत्रण करा आणि जास्त संक्रमित झाडे उपटून नष्ट करा.",
    },
    "Tomato mosaic virus": {
        "name": "टोमॅटो मोझॅक विषाणू",
        "cause": "पानांवर मोझॅकसारखी रंगछटा आणि वाढ खुंटणे हे याची लक्षणे आहेत.",
        "cure": "संक्रमित झाडे दूर करा, साधने निर्जंतुक ठेवा आणि निरोगी रोपे वापरा.",
    },
    "Leaf scorch": {
        "name": "पान भाजणे",
        "cause": "पानांच्या कडा करपल्यासारख्या दिसतात; हे बुरशीजन्य किंवा ताणाशी संबंधित असू शकते.",
        "cure": "संक्रमित पाने काढा, योग्य अंतर ठेवा आणि शिफारस केलेले बुरशीनाशक वापरा.",
    },
    "No leaf detected": {
        "name": "पान आढळले नाही",
        "cause": "अपलोड केलेल्या प्रतिमेत स्पष्ट पान दिसत नाही.",
        "cure": "नैसर्गिक प्रकाशात एकच पान स्पष्ट दिसेल असा फोटो पुन्हा घ्या.",
    },
    "Error": {
        "name": "त्रुटी",
        "cause": "दिलेल्या माहितीचे विश्लेषण करता आले नाही.",
        "cure": "स्पष्ट पानाचा फोटो वापरून पुन्हा प्रयत्न करा.",
    },
}

MARKET_CROP_TRANSLATIONS = {
    "Onion": "कांदा",
    "Grapes": "द्राक्षे",
    "Tomato": "टोमॅटो",
    "Wheat": "गहू",
    "Maize": "मका",
    "Cotton": "कापूस",
    "Soybean": "सोयाबीन",
    "Banana": "केळी",
    "Paddy": "भात",
    "Groundnut": "भुईमूग",
    "Sugarcane": "ऊस",
    "Potato": "बटाटा",
    "Cabbage": "कोबी",
    "Pomegranate": "डाळिंब",
    "Strawberry": "स्ट्रॉबेरी",
    "Ginger": "आले",
    "Turmeric": "हळद",
    "Corn": "मका",
    "Alphonso Mango": "हापूस आंबा",
    "Cashew": "काजू",
    "Coconut": "नारळ",
    "Kokum": "कोकम",
    "Sapota": "चिकू",
    "Brinjal": "वांगी",
    "Vegetable Mix": "भाजीपाला मिश्रण",
    "Fish (dried)": "सुकी मासळी",
    "Orange": "संत्री",
    "Tur Dal": "तूर डाळ",
    "Capsicum": "सिमला मिरची",
    "Jackfruit": "फणस",
}

DISTRICT_TRANSLATIONS = {
    "Nashik": "नाशिक",
    "Dhule": "धुळे",
    "Nandurbar": "नंदुरबार",
    "Jalgaon": "जळगाव",
    "Ahmednagar": "अहमदनगर",
    "Pune": "पुणे",
    "Solapur": "सोलापूर",
    "Satara": "सातारा",
    "Sangli": "सांगली",
    "Kolhapur": "कोल्हापूर",
    "Ratnagiri": "रत्नागिरी",
    "Sindhudurg": "सिंधुदुर्ग",
    "Palghar": "पालघर",
    "Thane": "ठाणे",
    "Raigad": "रायगड",
    "Mumbai": "मुंबई",
    "Nagpur": "नागपूर",
    "Amravati": "अमरावती",
    "Akola": "अकोला",
    "Washim": "वाशीम",
    "Buldhana": "बुलढाणा",
    "Wardha": "वर्धा",
    "Yavatmal": "यवतमाळ",
    "Chandrapur": "चंद्रपूर",
    "Gadchiroli": "गडचिरोली",
    "Bhandara": "भंडारा",
    "Gondia": "गोंदिया",
    "Aurangabad": "औरंगाबाद",
    "Jalna": "जालना",
    "Parbhani": "परभणी",
    "Hingoli": "हिंगोली",
    "Nanded": "नांदेड",
    "Latur": "लातूर",
    "Osmanabad": "उस्मानाबाद",
    "Beed": "बीड",
    "Sakri": "साक्री",
    "Maharashtra": "महाराष्ट्र",
}

AREA_GENERIC_TRANSLATIONS = {
    "Use protectant fungicides": "संरक्षक बुरशीनाशकांचा वापर करा.",
    "Prune infected wood and spray": "संक्रमित भाग छाटून फवारणी करा.",
    "Remove galls and apply fungicide": "गाठी काढून टाका आणि बुरशीनाशक फवारणी करा.",
    "Apply sulfur or systemic fungicide": "सल्फर किंवा प्रणालीगत बुरशीनाशक वापरा.",
    "Apply fungicide at early stage": "सुरुवातीच्या अवस्थेत बुरशीनाशक फवारणी करा.",
    "Spray resistance varieties and fungicides": "प्रतिरोधक वाण वापरा आणि गरजेनुसार फवारणी करा.",
    "Use protectant or systemic fungicide": "संरक्षक किंवा प्रणालीगत बुरशीनाशक वापरा.",
    "Remove infected wood and seal cuts": "संक्रमित लाकूड काढा आणि छाटलेल्या भागांचे संरक्षण करा.",
    "Spray fungicide at first sign": "पहिली लक्षणे दिसताच बुरशीनाशक फवारणी करा.",
    "Manage psyllids and remove infected trees": "सायलिड कीटक नियंत्रणात ठेवा आणि संक्रमित झाडे काढा.",
    "Apply copper based sprays": "तांब्याधारित फवारणी करा.",
    "Apply copper bactericide": "तांब्याधारित जीवाणूनाशक वापरा.",
    "Apply protectant fungicide regularly": "संरक्षक बुरशीनाशक नियमित वापरा.",
    "Apply systemic fungicide immediately": "ताबडतोब प्रणालीगत बुरशीनाशक वापरा.",
    "Apply sulfur or specific fungicide": "सल्फर किंवा विशिष्ट बुरशीनाशक वापरा.",
    "Apply fungicide and improve spacing": "बुरशीनाशक फवारणीसोबत योग्य अंतर ठेवा.",
    "Improve ventilation and apply fungicide": "हवेशीरपणा वाढवा आणि बुरशीनाशक वापरा.",
    "Apply specific acaricide": "विशिष्ट अॅकारिसाइड वापरा.",
    "Apply systemic fungicide": "प्रणालीगत बुरशीनाशक वापरा.",
    "Manage vector (whitefly) population": "पांढरी माशी या वाहक कीटकांचे नियंत्रण करा.",
    "Remove infected plants and sanitize": "संक्रमित झाडे काढून टाका आणि स्वच्छता राखा.",
    "Regular monitoring and balanced fertilization": "नियमित पाहणी आणि संतुलित खत व्यवस्थापन ठेवा.",
    "Maintain soil pH and moisture": "मातीचा pH आणि ओलावा योग्य ठेवा.",
    "Regular pruning and balanced nutrition": "नियमित छाटणी आणि संतुलित पोषण ठेवा.",
    "Weed management and timely irrigation": "तणनियंत्रण आणि वेळेवर सिंचन करा.",
    "Canopy management and timely nutrition": "छत्र व्यवस्थापन आणि वेळेवर पोषण द्या.",
    "Ensure proper drainage and nutrition": "पाण्याचा निचरा आणि पोषण योग्य ठेवा.",
    "Maintain good ventilation and soil health": "हवेशीरपणा आणि मातीचे आरोग्य चांगले ठेवा.",
    "Crop rotation and proper hilling": "पीक फेरपालट आणि योग्य बांधणी करा.",
    "Maintain sanitation and good air flow": "स्वच्छता आणि चांगला हवाप्रवाह राखा.",
    "Mulching and proper spacing": "मल्चिंग करा आणि योग्य अंतर ठेवा.",
    "Staking and lower leaf removal": "आधार द्या आणि खालची पाने वेळेवर काढा.",
    "Seed treatment and timely weeding": "बियाणे प्रक्रिया आणि वेळेवर खुरपणी करा.",
    "Bacterial": "जीवाणूजन्य समस्या नियंत्रणासाठी स्वच्छता आणि तांब्याधारित उपाय वापरा.",
}

AREA_VALUE_TRANSLATIONS = {
    "Nationally Registered": "राष्ट्रीय नोंदणीकृत",
    "Prevention Only": "फक्त प्रतिबंधासाठी",
    "Standard Practice": "मानक शिफारस",
    "Approved Product": "मान्यताप्राप्त उत्पादन",
    "Approved Products": "मान्यताप्राप्त उत्पादने",
    "Botanical Method": "वनस्पती-आधारित पद्धत",
    "ICAR Approved": "आयसीएआर मान्यताप्राप्त",
    "Registered Product": "नोंदणीकृत उत्पादन",
    "Traditional Formula": "पारंपरिक सूत्र",
    "Traditional Method": "पारंपरिक पद्धत",
    "Available in Krushi Kendra": "कृषी केंद्रात उपलब्ध",
    "Available in Mahabaleshwar": "महाबळेश्वर परिसरात उपलब्ध",
    "Available in Nashik": "नाशिकमध्ये उपलब्ध",
    "Available in Nashik Vineyards": "नाशिक द्राक्षबाग भागात उपलब्ध",
    "Available in Pune Division": "पुणे विभागात उपलब्ध",
    "Available in Vidarbha": "विदर्भात उपलब्ध",
    "Available in Vineyards": "द्राक्षबाग भागात उपलब्ध",
    "Available through Cooperatives": "सहकारी संस्थांमार्फत उपलब्ध",
    "Limited Availability": "मर्यादित उपलब्धता",
    "Widely Available": "मोठ्या प्रमाणावर उपलब्ध",
    "N/A": "लागू नाही",
}


def normalize_text(value: str) -> str:
    value = (value or "").lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[_/|(),:-]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def humanize_label(value: str) -> str:
    value = (value or "").replace("_", " ").replace(",", "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_class_name(class_name: str) -> tuple[str, str]:
    if class_name == BACKGROUND_CLASS:
        return "Unknown", "No leaf detected"
    crop_raw, _, disease_raw = class_name.partition("___")
    crop = humanize_label(crop_raw)
    disease = humanize_label(disease_raw or "Healthy")
    return crop, disease


def translate_crop_name(name: str) -> str:
    return CROP_TRANSLATIONS.get(name or "", name or "")


def translate_market_crop(name: str) -> str:
    return MARKET_CROP_TRANSLATIONS.get(name or "", translate_crop_name(name or ""))


def translate_district_name(name: str) -> str:
    return DISTRICT_TRANSLATIONS.get(name or "", name or "")


def disease_localization(disease: str) -> dict:
    return DISEASE_TRANSLATIONS.get(disease or "", {})


CLASS_NAME_LOOKUP: dict[tuple[str, str], str] = {}
for _class_name in IDX_TO_CLASSES.values():
    _crop, _disease = parse_class_name(_class_name)
    CLASS_NAME_LOOKUP[(normalize_text(_crop), normalize_text(_disease))] = _class_name
    localized = DISEASE_TRANSLATIONS.get(_disease, {})
    if localized.get("name"):
        CLASS_NAME_LOOKUP[(normalize_text(translate_crop_name(_crop)), normalize_text(localized["name"]))] = _class_name


def to_marathi_digits(value) -> str:
    return str(value).translate(MARATHI_DIGITS)


def format_datetime_mr(value, *, fallback: str = "—") -> str:
    if not value:
        return fallback
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    if not isinstance(value, datetime):
        return fallback
    return to_marathi_digits(value.strftime("%d-%m-%Y, %H:%M"))


def localize_class(class_name: str) -> dict:
    crop, disease = parse_class_name(class_name)
    localized_crop = translate_crop_name(crop)

    if class_name == BACKGROUND_CLASS:
        info = DISEASE_TRANSLATIONS["No leaf detected"]
        return {
            "crop": "अज्ञात",
            "disease": info["name"],
            "title": info["name"],
            "cause": info["cause"],
            "cure": info["cure"],
        }

    if class_name.endswith("___healthy"):
        disease_name = "निरोगी"
        return {
            "crop": localized_crop,
            "disease": disease_name,
            "title": f"{localized_crop} निरोगी",
            "cause": "रोगाची स्पष्ट लक्षणे दिसत नाहीत.",
            "cure": "योग्य सिंचन, संतुलित खत आणि नियमित पाहणी सुरू ठेवा.",
        }

    info = disease_localization(disease)
    localized_disease = info.get("name", disease)
    return {
        "crop": localized_crop,
        "disease": localized_disease,
        "title": f"{localized_crop} {localized_disease}",
        "cause": info.get("cause", "लक्षणांवरून रोगाचा संशय आहे. शेतात जवळील पाने तपासा."),
        "cure": info.get("cure", "शिफारस केलेले संरक्षण उपाय त्वरित सुरू करा."),
    }


def infer_class_name(crop: str = "", disease: str = "") -> str | None:
    key = (normalize_text(crop), normalize_text(disease))
    if key in CLASS_NAME_LOOKUP:
        return CLASS_NAME_LOOKUP[key]
    return None


def translate_area_value(value: str) -> str:
    return AREA_VALUE_TRANSLATIONS.get((value or "").strip(), value or "")


def translate_area_advice(value: str) -> str:
    return AREA_GENERIC_TRANSLATIONS.get((value or "").strip(), value or "")
