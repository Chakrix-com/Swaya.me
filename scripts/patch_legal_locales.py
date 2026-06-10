#!/usr/bin/env python3
"""
Patch all non-English locale files with:
  1. Correct lastUpdated date (June 2026) in each language
  2. Updated terms.s8Body (Apache 2.0 open source — old text was factually wrong)
  3. Add all new keys as English fallback (feature11-13, openSource*, proctoring sections)
     i18next already falls back to English for missing keys, but explicit inclusion
     avoids "key not found" warnings and ensures consistent behaviour.

For minor feature-description tweaks (feature1, feature2, etc.) the existing translated
text is close enough for Beta — those are left unchanged.
"""

import json, os

LOCALES_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src', 'locales')

# ── 1. lastUpdated in each language ──────────────────────────────────────────
LAST_UPDATED = {
    'hi': 'अंतिम अपडेट: जून 2026',
    'ta': 'கடைசியாக புதுப்பிக்கப்பட்டது: ஜூன் 2026',
    'te': 'చివరిగా నవీకరించబడింది: జూన్ 2026',
    'ka': 'ಕೊನೆಯದಾಗಿ ನವೀಕರಿಸಲಾಗಿದೆ: ಜೂನ್ 2026',
    'bn': 'সর্বশেষ আপডেট: জুন 2026',
    'gu': 'છેલ્લે અપડેટ: જૂન 2026',
    'es': 'Última actualización: junio de 2026',
    'fr': 'Dernière mise à jour : juin 2026',
    'de': 'Zuletzt aktualisiert: Juni 2026',
    'ru': 'Последнее обновление: июнь 2026',
}

# ── 2. terms.s8Body — Apache 2.0 (translated; old text was wrong) ────────────
TERMS_S8 = {
    'hi': (
        'Swaya.me प्लेटफ़ॉर्म का सोर्स कोड Apache License 2.0 के तहत जारी किया गया है और GitHub पर '
        'स्वतंत्र रूप से उपलब्ध है। आप उस लाइसेंस के अनुसार सोर्स कोड का उपयोग, कॉपी, संशोधन और '
        'वितरण कर सकते हैं। Swaya.me का नाम, लोगो और ब्रांडिंग Chakrix के ट्रेडमार्क हैं और '
        'अंतर्निहित कोड पर ओपन-सोर्स लाइसेंस के बावजूद पूर्व लिखित अनुमति के बिना इनका उपयोग '
        'नहीं किया जा सकता।'
    ),
    'ta': (
        'Swaya.me இயங்குதள மூலக்குறியீடு Apache License 2.0 இன் கீழ் வெளியிடப்பட்டுள்ளது மற்றும் '
        'GitHub இல் இலவசமாகக் கிடைக்கிறது. அந்த உரிமத்திற்கு இணங்க நீங்கள் மூலக்குறியீட்டைப் '
        'பயன்படுத்தலாம், நகலெடுக்கலாம், மாற்றலாம் மற்றும் விநியோகிக்கலாம். Swaya.me பெயர், '
        'லோகோ மற்றும் பிராண்டிங் Chakrix இன் வர்த்தக முத்திரைகள் மற்றும் அடிப்படைக் குறியீட்டில் '
        'திறந்த மூல உரிமம் இருந்தாலும் முன் எழுத்துப்பூர்வ அனுமதி இல்லாமல் பயன்படுத்த முடியாது.'
    ),
    'te': (
        'Swaya.me ప్లాట్‌ఫారమ్ సోర్స్ కోడ్ Apache License 2.0 కింద విడుదల చేయబడింది మరియు '
        'GitHub లో అందుబాటులో ఉంది. మీరు ఆ లైసెన్స్ ప్రకారం సోర్స్ కోడ్‌ను ఉపయోగించవచ్చు, '
        'కాపీ చేయవచ్చు, సవరించవచ్చు మరియు పంపిణీ చేయవచ్చు. Swaya.me పేరు, లోగో మరియు '
        'బ్రాండింగ్ Chakrix యొక్క ట్రేడ్‌మార్క్‌లు మరియు అంతర్లీన కోడ్‌పై ఓపెన్-సోర్స్ లైసెన్స్ '
        'ఉన్నప్పటికీ ముందస్తు వ్రాతపూర్వక అనుమతి లేకుండా ఉపయోగించకూడదు.'
    ),
    'ka': (
        'Swaya.me ಪ್ಲಾಟ್‌ಫಾರ್ಮ್‌ನ ಸೋರ್ಸ್ ಕೋಡ್ ಅನ್ನು Apache License 2.0 ಅಡಿಯಲ್ಲಿ ಬಿಡುಗಡೆ ಮಾಡಲಾಗಿದೆ '
        'ಮತ್ತು GitHub ನಲ್ಲಿ ಲಭ್ಯವಿದೆ. ಆ ಪರವಾನಗಿಗೆ ಅನುಸಾರವಾಗಿ ನೀವು ಸೋರ್ಸ್ ಕೋಡ್ ಅನ್ನು '
        'ಬಳಸಬಹುದು, ನಕಲಿಸಬಹುದು, ಮಾರ್ಪಡಿಸಬಹುದು ಮತ್ತು ವಿತರಿಸಬಹುದು. Swaya.me ಹೆಸರು, ಲೋಗೋ '
        'ಮತ್ತು ಬ್ರ್ಯಾಂಡಿಂಗ್ Chakrix ನ ಟ್ರೇಡ್‌ಮಾರ್ಕ್‌ಗಳಾಗಿದ್ದು, ಆಧಾರವಾಗಿರುವ ಕೋಡ್‌ನಲ್ಲಿ '
        'ಓಪನ್-ಸೋರ್ಸ್ ಪರವಾನಗಿ ಇದ್ದರೂ ಪೂರ್ವ ಲಿಖಿತ ಅನುಮತಿ ಇಲ್ಲದೆ ಬಳಸಲಾಗುವುದಿಲ್ಲ.'
    ),
    'bn': (
        'Swaya.me প্ল্যাটফর্মের সোর্স কোড Apache License 2.0 এর অধীনে প্রকাশিত এবং GitHub এ '
        'বিনামূল্যে পাওয়া যায়। আপনি সেই লাইসেন্স অনুযায়ী সোর্স কোড ব্যবহার, কপি, পরিবর্তন এবং '
        'বিতরণ করতে পারবেন। Swaya.me নাম, লোগো এবং ব্র্যান্ডিং Chakrix এর ট্রেডমার্ক এবং '
        'অন্তর্নিহিত কোডে ওপেন-সোর্স লাইসেন্স থাকলেও পূর্ব লিখিত অনুমতি ছাড়া ব্যবহার করা যাবে না।'
    ),
    'gu': (
        'Swaya.me પ્લેટફોર્મ સોર્સ કોડ Apache License 2.0 હેઠળ રિલીઝ કરવામાં આવ્યો છે અને '
        'GitHub પર મફત ઉપલબ્ધ છે। તમે તે લાઇસન્સ અનુસાર સોર્સ કોડ ઉપયોગ, કૉપિ, સુધારણા અને '
        'વિતરણ કરી શકો છો। Swaya.me નામ, લોગો અને બ્રાન્ડિંગ Chakrix ના ટ્રેડમાર્ક છે અને '
        'અંતર્નિહિત કોડ પર ઓપન-સોર્સ લાઇસન્સ હોવા છતાં અગાઉની લેખિત પરવાનગી વિના ઉપયોગ '
        'કરી શકાતો નથી.'
    ),
    'es': (
        'El código fuente de la plataforma Swaya.me está publicado bajo la Licencia Apache 2.0 y '
        'está disponible libremente en GitHub. Puedes usar, copiar, modificar y distribuir el código '
        'fuente de acuerdo con dicha licencia. El nombre, logotipo y marca de Swaya.me son marcas '
        'registradas de Chakrix y no pueden utilizarse sin permiso previo por escrito, '
        'independientemente de la licencia de código abierto del código subyacente.'
    ),
    'fr': (
        'Le code source de la plateforme Swaya.me est publié sous la licence Apache 2.0 et est '
        'librement disponible sur GitHub. Vous pouvez utiliser, copier, modifier et distribuer le '
        'code source conformément à cette licence. Le nom, le logo et la marque Swaya.me sont des '
        'marques de commerce de Chakrix et ne peuvent pas être utilisés sans autorisation écrite '
        'préalable, quelle que soit la licence open source du code sous-jacent.'
    ),
    'de': (
        'Der Quellcode der Swaya.me-Plattform wird unter der Apache License 2.0 veröffentlicht und '
        'ist auf GitHub frei verfügbar. Sie dürfen den Quellcode gemäß dieser Lizenz verwenden, '
        'kopieren, modifizieren und verteilen. Der Name, das Logo und die Marke Swaya.me sind '
        'Markenzeichen von Chakrix und dürfen unabhängig von der Open-Source-Lizenz des '
        'zugrundeliegenden Codes nicht ohne vorherige schriftliche Genehmigung verwendet werden.'
    ),
    'ru': (
        'Исходный код платформы Swaya.me выпущен под лицензией Apache License 2.0 и свободно '
        'доступен на GitHub. Вы можете использовать, копировать, изменять и распространять исходный '
        'код в соответствии с этой лицензией. Название, логотип и бренд Swaya.me являются '
        'товарными знаками Chakrix и не могут использоваться без предварительного письменного '
        'разрешения, независимо от лицензии с открытым исходным кодом на базовый код.'
    ),
}

# ── 3. New keys — English fallback (these will be written to all locales so
#    i18next doesn't log "key missing" warnings; users on non-English get
#    English for these new additions which is acceptable for Beta) ────────────
NEW_KEYS_EN = {
    'pages.about.feature11': (
        'AI question generation — describe a topic and Gemini AI creates ready-to-use questions instantly'
    ),
    'pages.about.feature12': (
        'Exam proctoring — optional webcam monitoring, fullscreen enforcement, and violation detection for Test sessions'
    ),
    'pages.about.feature13': (
        'Templates and folder organisation — reuse content from the platform library and keep your activities neatly grouped'
    ),
    'pages.about.openSourceTitle': 'Open Source',
    'pages.about.openSourceBody': (
        'Swaya.me is open source, released under the Apache License 2.0. The full source code is publicly '
        'available on GitHub — you are free to self-host, fork, contribute, or build on it. '
        'Contributions and bug reports are welcome.'
    ),
    'pages.about.openSourceGithub': 'Source code on GitHub:',
    'pages.about.openSourceLicense': 'License:',
    'pages.privacy.s1Body4Label': 'Proctoring data (Exam sessions only):',
    'pages.privacy.s1Body4': (
        'When a host enables proctoring on an Exam (Test) session, periodic webcam snapshots are captured '
        'from participants\' devices during the session for exam integrity purposes. Participants are shown '
        'an explicit notice and must grant camera access before joining a proctored session. These images '
        'are stored securely, are accessible only to the session host, and are not shared with any third party. '
        'They are deleted when the host removes the session history.'
    ),
    'pages.privacy.s2li6': (
        'To support exam integrity where proctoring is enabled '
        '(webcam snapshots made available to the session host only)'
    ),
    'pages.terms.s1Body3': (
        'Certain Exam sessions may use optional proctoring features (webcam monitoring, fullscreen enforcement, '
        'and violation detection). Participants are shown an explicit notice and must grant camera access before '
        'joining a proctored session. By doing so, participants consent to the capture of periodic webcam snapshots '
        'for exam integrity purposes. Hosts are solely responsible for informing their participants about proctoring '
        'in advance and for complying with applicable laws regarding monitoring.'
    ),
}


def set_nested(d: dict, dotkey: str, value: str):
    keys = dotkey.split('.')
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def get_nested(d: dict, dotkey: str):
    node = d
    for k in dotkey.split('.'):
        if not isinstance(node, dict) or k not in node:
            return None
        node = node[k]
    return node


def patch_locale(lang: str):
    path = os.path.join(LOCALES_DIR, lang, 'translation.json')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    changes = []

    # 1. lastUpdated date
    set_nested(data, 'pages.legal.lastUpdated', LAST_UPDATED[lang])
    changes.append('lastUpdated')

    # 2. terms.s8Body — Apache 2.0 (translated)
    set_nested(data, 'pages.terms.s8Body', TERMS_S8[lang])
    changes.append('terms.s8Body')

    # 3. New keys — English fallback (only write if key doesn't already exist)
    for dotkey, en_val in NEW_KEYS_EN.items():
        if get_nested(data, dotkey) is None:
            set_nested(data, dotkey, en_val)
            changes.append(dotkey)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')

    print(f'[{lang}] {len(changes)} keys updated: {", ".join(changes[:4])}{"…" if len(changes)>4 else ""}')


if __name__ == '__main__':
    langs = ['hi', 'ta', 'te', 'ka', 'bn', 'gu', 'es', 'fr', 'de', 'ru']
    for lang in langs:
        patch_locale(lang)
    print('\nDone — all 10 locales patched.')
