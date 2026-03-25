# Plan — In-App Navigation Guidance (Tooltips & Hints)

> **Status:** Draft — not yet implemented
> **Date:** 2026-03-25

---

## Is Tooltip the Best Approach?

Short answer: **tooltips alone are not enough.** A layered approach works better:

| Pattern | When to use | Examples in this plan |
|---|---|---|
| **Tooltip** (hover, ≤10 words) | Icon-only buttons with no visible label | Theme toggle, Logout, Reveal Answer, History |
| **Info popover** (ⓘ click-triggered, 1–2 sentences) | Feature concepts a new user won't recognise | Already used for Create Quiz / Poll / Test / Offline Poll — extend this pattern |
| **Inline form hint** (`Form.Item help=` prop, grey text below field) | Input fields where the purpose isn't obvious | Points, Max Time, Negative Points, Expected Answer |
| **Empty-state guidance card** | When the quiz list is empty for new users | A visual card with the 4 quiz types and a "Start here" prompt |

**Recommendation:** Implement tooltips + inline hints (this plan) now. Defer an onboarding walkthrough tour to a later release — it requires a third-party library (`react-joyride`) and significant content work across 11 languages.

---

## Scope

**25 placements** across 4 areas. Skipping self-evident buttons (Edit, Delete, Cancel, Save) — tooltips on obvious labels add noise, not value.

---

## Placement & Copy

### Area 1 — Header / Layout (3 tooltips)

| # | Element | Component | i18n key | English copy |
|---|---|---|---|---|
| H1 | Theme toggle button (sun/moon icon) | `App.jsx` header | `tooltip.themeToggle` | Switch between light and dark mode |
| H2 | Language switcher | `App.jsx` header | `tooltip.languageSwitcher` | Change the display language |
| H3 | Logout button (icon only) | `App.jsx` header | `tooltip.logout` | Sign out of your account |

---

### Area 2 — Dashboard (8 tooltips / hints)

| # | Element | i18n key | Type | English copy |
|---|---|---|---|---|
| D1 | **Use Template** button | `tooltip.useTemplate` | Tooltip | Start from a ready-made quiz — edit and launch in minutes |
| D2 | **Star icon** — Make Template | `tooltip.makeTemplate` | Tooltip | Save as a reusable template for your workspace |
| D3 | **Star icon** — Remove Template | `tooltip.removeTemplate` | Tooltip | Remove from templates (quiz is kept) |
| D4 | **History** button (clock icon) | `tooltip.quizHistory` | Tooltip | View past session results and participant scores |
| D5 | **Start Quiz** button | `tooltip.startSession` | Tooltip | Launch a live session — share the join code with your audience |
| D6 | **Create Quiz** info icon (ⓘ) | `quiz.quizTypeInfo` | Already exists — update copy | Live, host-controlled session. MCQ questions with scoring. Real-time leaderboard. Audience joins via a code. |
| D7 | **Create Poll** info icon (ⓘ) | `quiz.pollTypeInfo` | Already exists — update copy | Live, host-controlled session. Open MCQ or word cloud questions — no correct answer, no scoring. |
| D8 | **Create Offline Poll** info icon (ⓘ) | `offlinePoll.typeInfo` | Already exists — update copy | No live host needed. Share a link — audience responds at their own pace. Results accumulate over time. |
| D9 | **Create Test** info icon (ⓘ) | `exam.typeInfo` | Already exists — update copy | Timed, self-paced exam. Auto-scored with +/− points. Participants receive a rank and score at the end. |

> D6–D9 already have ⓘ icons and keys. Only the copy is updated — no new implementation.

---

### Area 3 — Quiz Builder (10 inline hints + tooltips)

| # | Element | i18n key | Type | English copy |
|---|---|---|---|---|
| B1 | **Publish** button | `tooltip.publishQuiz` | Tooltip | Make this quiz ready to run. You can still edit it after publishing. |
| B2 | **Unpublish** button | `tooltip.unpublishQuiz` | Tooltip | Move back to draft to make edits |
| B3 | **Copy Link** (offline poll / exam) | `tooltip.copyShareLink` | Tooltip | Copy the link to share directly with your audience |
| B4 | **Points** field | `tooltip.questionPoints` | Inline hint | Points awarded for a correct answer |
| B5 | **Max Time** field | `tooltip.maxTime` | Inline hint | Auto-advances the question after this many seconds. Leave empty for no limit. |
| B6 | **Negative Points** field (exam only) | `tooltip.negativePoints` | Inline hint | Points deducted for a wrong answer. Set to 0 to disable negative marking. |
| B7 | **Expected Answer** field (single-line / paragraph) | `tooltip.expectedAnswer` | Inline hint | Model answer — Swaya uses AI to mark responses based on meaning, not exact wording |
| B8 | **Simple / Rich Text** question toggle | `tooltip.richTextToggleQuestion` | Tooltip | Switch to rich text to add bold, tables, code, and colour in your question |
| B9 | **Simple / Rich Text** options toggle | `tooltip.richTextToggleOptions` | Tooltip | Format answer options with bold, italic, and other styles |
| B10 | **Scale question** correct answer | `tooltip.scaleCorrectAnswer` | Inline hint | The scale value (1–5) that will be marked as the correct answer |

---

### Area 4 — Quiz Control / Live Session (4 tooltips)

| # | Element | i18n key | Type | English copy |
|---|---|---|---|---|
| C1 | **Reveal Answer** button | `tooltip.revealAnswer` | Tooltip | Show participants which answer was correct |
| C2 | **Session join code** input | `tooltip.sessionCode` | Inline hint | Share this code — participants go to swaya.me and enter it to join |
| C3 | **Present (Immersive)** button | `quizPresent.presentImmersiveTooltip` | Already exists | Open immersive presenter mode in a new tab for audience-facing display |
| C4 | **Stop Quiz** button | `tooltip.stopQuiz` | Tooltip | End the live session. Results are saved and available in History. |

---

## Empty State Guidance (New — Dashboard)

When a user has **zero quizzes**, the quiz list currently shows "No quizzes found." Replace this with a guidance card that explains the 4 quiz types and invites them to create their first one.

| i18n key | English copy |
|---|---|
| `tooltip.emptyStateTitle` | Create your first quiz |
| `tooltip.emptyStateSubtitle` | Choose the type that fits your use case |
| `tooltip.emptyStateQuizDesc` | Live Quiz — run with an audience in real time |
| `tooltip.emptyStatePollDesc` | Live Poll — gather instant audience responses |
| `tooltip.emptyStateOfflinePollDesc` | Offline Poll — share a link, collect responses anytime |
| `tooltip.emptyStateExamDesc` | Test / Exam — timed, auto-scored, shareable via link |

---

## All Translations

> All 25 placement strings + 6 empty-state strings across all 11 languages.
> Keys use the `tooltip.*` namespace (new) to keep them grouped.
> Already-existing keys (D6–D9, C3) are shown under their existing namespaces.

---

### New `tooltip` namespace keys

#### `tooltip.themeToggle`
| Lang | Translation |
|------|-------------|
| en | Switch between light and dark mode |
| hi | लाइट और डार्क मोड के बीच स्विच करें |
| ta | ஒளி மற்றும் இருண்ட பயன்முறைக்கு மாறவும் |
| te | లైట్ మరియు డార్క్ మోడ్ మధ్య మారండి |
| ka | ಬೆಳಕು ಮತ್ತು ಡಾರ್ಕ್ ಮೋಡ್ ನಡುವೆ ಬದಲಾಯಿಸಿ |
| bn | লাইট এবং ডার্ক মোডের মধ্যে স্যুইচ করুন |
| gu | લાઇટ અને ડાર્ક મોડ વચ્ચે સ્વિચ કરો |
| es | Cambiar entre modo claro y oscuro |
| fr | Basculer entre le mode clair et sombre |
| de | Zwischen hellem und dunklem Modus wechseln |
| ru | Переключение между светлым и тёмным режимом |

#### `tooltip.languageSwitcher`
| Lang | Translation |
|------|-------------|
| en | Change the display language |
| hi | प्रदर्शन भाषा बदलें |
| ta | காட்சி மொழியை மாற்றவும் |
| te | ప్రదర్శన భాషను మార్చండి |
| ka | ಪ್ರದರ್ಶನ ಭಾಷೆ ಬದಲಾಯಿಸಿ |
| bn | প্রদর্শন ভাষা পরিবর্তন করুন |
| gu | પ્રદર્શન ભાષા બદલો |
| es | Cambiar el idioma de visualización |
| fr | Changer la langue d'affichage |
| de | Anzeigesprache ändern |
| ru | Изменить язык интерфейса |

#### `tooltip.logout`
| Lang | Translation |
|------|-------------|
| en | Sign out of your account |
| hi | अपने खाते से साइन आउट करें |
| ta | உங்கள் கணக்கிலிருந்து வெளியேறவும் |
| te | మీ ఖాతా నుండి సైన్ అవుట్ చేయండి |
| ka | ನಿಮ್ಮ ಖಾತೆಯಿಂದ ಸೈನ್ ಔಟ್ ಮಾಡಿ |
| bn | আপনার অ্যাকাউন্ট থেকে সাইন আউট করুন |
| gu | તમારા એકાઉન્ટમાંથી સાઇન આઉટ કરો |
| es | Cerrar sesión en tu cuenta |
| fr | Se déconnecter de votre compte |
| de | Von Ihrem Konto abmelden |
| ru | Выйти из своей учётной записи |

#### `tooltip.useTemplate`
| Lang | Translation |
|------|-------------|
| en | Start from a ready-made quiz — edit and launch in minutes |
| hi | तैयार क्विज़ से शुरू करें — मिनटों में संपादित करें और लॉन्च करें |
| ta | தயாரான வினாடி வினாவிலிருந்து தொடங்கவும் — நிமிடங்களில் திருத்தி தொடங்கவும் |
| te | సిద్ధంగా ఉన్న క్విజ్ నుండి ప్రారంభించండి — నిమిషాల్లో సవరించి ప్రారంభించండి |
| ka | ಸಿದ್ಧ ರಸಪ್ರಶ್ನೆಯಿಂದ ಪ್ರಾರಂಭಿಸಿ — ನಿಮಿಷಗಳಲ್ಲಿ ಸಂಪಾದಿಸಿ ಮತ್ತು ಪ್ರಾರಂಭಿಸಿ |
| bn | একটি রেডিমেড কুইজ থেকে শুরু করুন — মিনিটের মধ্যে সম্পাদনা করুন এবং চালু করুন |
| gu | તૈયાર ક્વિઝથી શરૂ કરો — મિનિટોમાં સંપાદિત કરો અને લૉન્ચ કરો |
| es | Empieza con un cuestionario listo — edita y lanza en minutos |
| fr | Commencez avec un quiz prêt à l'emploi — modifiez et lancez en quelques minutes |
| de | Mit einem fertigen Quiz starten — in Minuten bearbeiten und starten |
| ru | Начните с готовой викторины — редактируйте и запускайте за минуты |

#### `tooltip.makeTemplate`
| Lang | Translation |
|------|-------------|
| en | Save as a reusable template for your workspace |
| hi | अपने कार्यक्षेत्र के लिए पुनः उपयोग करने योग्य टेम्पलेट के रूप में सहेजें |
| ta | உங்கள் பணியிடத்திற்கு மீண்டும் பயன்படுத்தக்கூடிய வார்ப்புருவாக சேமிக்கவும் |
| te | మీ వర్క్‌స్పేస్‌కు పునర్వినియోగ టెంప్లేట్‌గా సేవ్ చేయండి |
| ka | ನಿಮ್ಮ ವರ್ಕ್‌ಸ್ಪೇಸ್‌ಗಾಗಿ ಮರುಬಳಕೆಯ ಟೆಂಪ್ಲೇಟ್ ಆಗಿ ಉಳಿಸಿ |
| bn | আপনার ওয়ার্কস্পেসের জন্য পুনর্ব্যবহারযোগ্য টেমপ্লেট হিসেবে সংরক্ষণ করুন |
| gu | તમારા વર્કસ્પેસ માટે ફરીથી વાપરી શકાય તેવા ટેમ્પ્લેટ તરીકે સંગ્રહ કરો |
| es | Guardar como plantilla reutilizable para tu espacio de trabajo |
| fr | Enregistrer comme modèle réutilisable pour votre espace de travail |
| de | Als wiederverwendbare Vorlage für Ihren Arbeitsbereich speichern |
| ru | Сохранить как многоразовый шаблон для вашего рабочего пространства |

#### `tooltip.removeTemplate`
| Lang | Translation |
|------|-------------|
| en | Remove from templates (quiz is kept) |
| hi | टेम्पलेट से हटाएं (क्विज़ सुरक्षित रहती है) |
| ta | வார்ப்புருக்களிலிருந்து அகற்றவும் (வினாடி வினா வைக்கப்படும்) |
| te | టెంప్లేట్‌ల నుండి తొలగించండి (క్విజ్ భద్రపరచబడుతుంది) |
| ka | ಟೆಂಪ್ಲೇಟ್‌ಗಳಿಂದ ತೆಗೆದುಹಾಕಿ (ರಸಪ್ರಶ್ನೆ ಉಳಿಸಲಾಗುತ್ತದೆ) |
| bn | টেমপ্লেট থেকে সরান (কুইজ রাখা হবে) |
| gu | ટેમ્પ્લેટ્સમાંથી દૂર કરો (ક્વિઝ સાચવવામાં આવશે) |
| es | Quitar de plantillas (el cuestionario se conserva) |
| fr | Supprimer des modèles (le quiz est conservé) |
| de | Aus Vorlagen entfernen (Quiz bleibt erhalten) |
| ru | Удалить из шаблонов (викторина сохраняется) |

#### `tooltip.quizHistory`
| Lang | Translation |
|------|-------------|
| en | View past session results and participant scores |
| hi | पिछले सत्र के परिणाम और प्रतिभागी स्कोर देखें |
| ta | கடந்த கால அமர்வு முடிவுகள் மற்றும் பங்கேற்பாளர் மதிப்பெண்களை காணவும் |
| te | గత సెషన్ ఫలితాలు మరియు పాల్గొనేవారి స్కోర్‌లు చూడండి |
| ka | ಹಿಂದಿನ ಸೆಷನ್ ಫಲಿತಾಂಶಗಳು ಮತ್ತು ಭಾಗವಹಿಸುವವರ ಅಂಕಗಳನ್ನು ನೋಡಿ |
| bn | অতীতের সেশনের ফলাফল এবং অংশগ্রহণকারীদের স্কোর দেখুন |
| gu | ભૂતકાળના સત્ર પરિણામો અને સહભાગી સ્કોર જુઓ |
| es | Ver resultados de sesiones anteriores y puntuaciones de participantes |
| fr | Voir les résultats des sessions passées et les scores des participants |
| de | Vergangene Sitzungsergebnisse und Teilnehmerpunkte anzeigen |
| ru | Просмотр результатов прошлых сессий и баллов участников |

#### `tooltip.startSession`
| Lang | Translation |
|------|-------------|
| en | Launch a live session — share the join code with your audience |
| hi | लाइव सत्र शुरू करें — अपने दर्शकों के साथ जॉइन कोड साझा करें |
| ta | நேரடி அமர்வை தொடங்கவும் — உங்கள் பார்வையாளர்களுடன் சேர்தல் குறியீட்டை பகிரவும் |
| te | లైవ్ సెషన్ ప్రారంభించండి — మీ ప్రేక్షకులతో జాయిన్ కోడ్ పంచుకోండి |
| ka | ಲೈವ್ ಸೆಷನ್ ಪ್ರಾರಂಭಿಸಿ — ನಿಮ್ಮ ಪ್ರೇಕ್ಷಕರೊಂದಿಗೆ ಸೇರ್ಪಡೆ ಕೋಡ್ ಹಂಚಿಕೊಳ್ಳಿ |
| bn | একটি লাইভ সেশন চালু করুন — আপনার দর্শকদের সাথে জয়েন কোড শেয়ার করুন |
| gu | લાઇવ સત્ર શરૂ કરો — તમારા પ્રેક્ષકો સાથે જોઇન કોડ શેર કરો |
| es | Inicia una sesión en vivo — comparte el código de acceso con tu audiencia |
| fr | Lancer une session en direct — partagez le code d'accès avec votre audience |
| de | Live-Sitzung starten — Beitrittscode mit Ihrem Publikum teilen |
| ru | Запустить живую сессию — поделитесь кодом входа с вашей аудиторией |

#### `tooltip.publishQuiz`
| Lang | Translation |
|------|-------------|
| en | Make this quiz ready to run. You can still edit it after publishing. |
| hi | इस क्विज़ को चलाने के लिए तैयार करें। प्रकाशन के बाद भी संपादन कर सकते हैं। |
| ta | இந்த வினாடி வினாவை இயக்கத் தயாராக்கவும். வெளியிட்ட பிறகும் திருத்தலாம். |
| te | ఈ క్విజ్‌ను నడపడానికి సిద్ధం చేయండి. ప్రచురించిన తర్వాత కూడా సవరించవచ్చు. |
| ka | ಈ ರಸಪ್ರಶ್ನೆಯನ್ನು ಚಲಾಯಿಸಲು ಸಿದ್ಧಪಡಿಸಿ. ಪ್ರಕಟಿಸಿದ ನಂತರವೂ ಸಂಪಾದಿಸಬಹುದು. |
| bn | এই কুইজটি চালাতে প্রস্তুত করুন। প্রকাশের পরেও সম্পাদনা করা যাবে। |
| gu | આ ક્વિઝ ચલાવવા માટે તૈયાર કરો. પ્રકાશિત કર્યા પછી પણ સંપાદિત કરી શકાય છે. |
| es | Prepara este cuestionario para ejecutarse. Aún puedes editarlo después de publicar. |
| fr | Prépare ce quiz pour être lancé. Vous pouvez toujours le modifier après la publication. |
| de | Dieses Quiz startklar machen. Sie können es auch nach der Veröffentlichung bearbeiten. |
| ru | Подготовить викторину к запуску. После публикации её всё равно можно редактировать. |

#### `tooltip.unpublishQuiz`
| Lang | Translation |
|------|-------------|
| en | Move back to draft to make edits |
| hi | संपादन के लिए वापस ड्राफ्ट में ले जाएं |
| ta | திருத்தங்கள் செய்ய வரைவுக்கு திரும்பவும் |
| te | సవరణలు చేయడానికి తిరిగి డ్రాఫ్ట్‌కు తరలించండి |
| ka | ಸಂಪಾದನೆಗಾಗಿ ಮತ್ತೆ ಡ್ರಾಫ್ಟ್‌ಗೆ ತರলಿ |
| bn | সম্পাদনার জন্য ড্রাফটে ফিরিয়ে নিন |
| gu | ફેરફારો કરવા ડ્રાફ્ટ પર પાછા લો |
| es | Volver a borrador para hacer ediciones |
| fr | Repasser en brouillon pour effectuer des modifications |
| de | Zurück zu Entwurf zum Bearbeiten |
| ru | Вернуть в черновик для редактирования |

#### `tooltip.copyShareLink`
| Lang | Translation |
|------|-------------|
| en | Copy the link to share directly with your audience |
| hi | अपने दर्शकों के साथ सीधे साझा करने के लिए लिंक कॉपी करें |
| ta | உங்கள் பார்வையாளர்களுடன் நேரடியாக பகிர இணைப்பை நகலெடுக்கவும் |
| te | మీ ప్రేక్షకులతో నేరుగా పంచుకోవడానికి లింక్ కాపీ చేయండి |
| ka | ನಿಮ್ಮ ಪ್ರೇಕ್ಷಕರೊಂದಿಗೆ ನೇರವಾಗಿ ಹಂಚಿಕೊಳ್ಳಲು ಲಿಂಕ್ ನಕಲಿಸಿ |
| bn | আপনার দর্শকদের সাথে সরাসরি শেয়ার করতে লিঙ্ক কপি করুন |
| gu | તમારા પ્રેક્ષકો સાથે સીધો શેર કરવા લિંક કૉપિ કરો |
| es | Copiar el enlace para compartir directamente con tu audiencia |
| fr | Copier le lien pour le partager directement avec votre audience |
| de | Link kopieren, um ihn direkt mit Ihrem Publikum zu teilen |
| ru | Скопировать ссылку для прямого распространения среди аудитории |

#### `tooltip.questionPoints`
| Lang | Translation |
|------|-------------|
| en | Points awarded for a correct answer |
| hi | सही उत्तर के लिए दिए जाने वाले अंक |
| ta | சரியான பதிலுக்கு வழங்கப்படும் புள்ளிகள் |
| te | సరైన సమాధానానికి ఇవ్వబడే పాయింట్లు |
| ka | ಸರಿಯಾದ ಉತ್ತರಕ್ಕೆ ನೀಡಲಾಗುವ ಅಂಕಗಳು |
| bn | সঠিক উত্তরের জন্য প্রদত্ত পয়েন্ট |
| gu | સાચા જવાબ માટે આપવામાં આવતા પોઇન્ટ |
| es | Puntos otorgados por una respuesta correcta |
| fr | Points attribués pour une bonne réponse |
| de | Punkte für eine richtige Antwort |
| ru | Очки за правильный ответ |

#### `tooltip.maxTime`
| Lang | Translation |
|------|-------------|
| en | Auto-advances after this many seconds. Leave empty for no limit. |
| hi | इतने सेकंड बाद स्वचालित रूप से आगे बढ़ेगा। कोई सीमा नहीं रखने के लिए खाली छोड़ें। |
| ta | இத்தனை வினாடிகளுக்குப் பிறகு தானாக முன்னேறும். வரம்பில்லாமல் இருக்க காலியாக விடவும். |
| te | ఇన్ని సెకన్ల తర్వాత స్వయంచాలకంగా ముందుకు వెళ్తుంది. పరిమితి వద్దంటే ఖాళీగా ఉంచండి. |
| ka | ಇಷ್ಟು ಸೆಕೆಂಡ್‌ಗಳ ನಂತರ ಸ್ವಯಂಚಾಲಿತವಾಗಿ ಮುಂದಕ್ಕೆ ಹೋಗುತ್ತದೆ. ಮಿತಿ ಬೇಡದಿದ್ದರೆ ಖಾಲಿ ಬಿಡಿ. |
| bn | এত সেকেন্ড পরে স্বয়ংক্রিয়ভাবে এগিয়ে যাবে। কোনো সীমা না রাখতে খালি রাখুন। |
| gu | આટલી સેકન્ડ પછી આપોઆપ આગળ વધશે. મર્યાદા ન રાખવી હોય તો ખાલી રાખો. |
| es | Avanza automáticamente después de estos segundos. Deja vacío para sin límite. |
| fr | Avance automatiquement après ce nombre de secondes. Laissez vide pour aucune limite. |
| de | Rückt nach dieser Anzahl von Sekunden automatisch vor. Leer lassen für kein Limit. |
| ru | Автоматически переходит через указанное количество секунд. Оставьте пустым для отсутствия ограничения. |

#### `tooltip.negativePoints`
| Lang | Translation |
|------|-------------|
| en | Points deducted for a wrong answer. Set to 0 to disable. |
| hi | गलत उत्तर के लिए काटे जाने वाले अंक। अक्षम करने के लिए 0 सेट करें। |
| ta | தவறான பதிலுக்கு கழிக்கப்படும் புள்ளிகள். முடக்க 0 ஆக அமைக்கவும். |
| te | తప్పు సమాధానానికి తీసివేయబడే పాయింట్లు. నిలిపివేయడానికి 0 సెట్ చేయండి. |
| ka | ತಪ್ಪು ಉತ್ತರಕ್ಕೆ ಕಡಿತಗೊಳಿಸಲಾಗುವ ಅಂಕಗಳು. ನಿಷ್ಕ್ರಿಯಗೊಳಿಸಲು 0 ಹೊಂದಿಸಿ. |
| bn | ভুল উত্তরের জন্য কাটা যাওয়া পয়েন্ট। নিষ্ক্রিয় করতে 0 সেট করুন। |
| gu | ખોટા જવાબ માટે કાપવામાં આવતા પોઇન્ટ. બંધ કરવા 0 સેટ કરો. |
| es | Puntos deducidos por una respuesta incorrecta. Pon 0 para desactivar. |
| fr | Points déduits pour une mauvaise réponse. Mettre 0 pour désactiver. |
| de | Punkte für eine falsche Antwort abgezogen. Auf 0 setzen, um zu deaktivieren. |
| ru | Очки, вычитаемые за неправильный ответ. Установите 0 для отключения. |

#### `tooltip.expectedAnswer`
| Lang | Translation |
|------|-------------|
| en | Model answer — Swaya uses AI to mark by meaning, not exact wording |
| hi | आदर्श उत्तर — Swaya AI का उपयोग करके अर्थ के आधार पर जांचता है |
| ta | மாதிரி பதில் — Swaya AI ஐப் பயன்படுத்தி அர்த்தத்தின் அடிப்படையில் சரிபார்க்கிறது |
| te | మోడల్ సమాధానం — Swaya AI ని ఉపయోగించి అర్థం ఆధారంగా గుర్తిస్తుంది |
| ka | ಮಾದರಿ ಉತ್ತರ — Swaya AI ಬಳಸಿ ಅರ್ಥದ ಆಧಾರದ ಮೇಲೆ ಪರೀಕ್ಷಿಸುತ್ತದೆ |
| bn | মডেল উত্তর — Swaya AI ব্যবহার করে অর্থের ভিত্তিতে যাচাই করে |
| gu | આદર્શ જવાબ — Swaya AI વापરીને અર્થ આધારિત ચકાસણી કરે છે |
| es | Respuesta modelo — Swaya usa IA para calificar por significado, no por palabras exactas |
| fr | Réponse modèle — Swaya utilise l'IA pour noter par sens, pas par formulation exacte |
| de | Musterantwort — Swaya bewertet per KI nach Bedeutung, nicht nach genauen Worten |
| ru | Образцовый ответ — Swaya использует ИИ для проверки по смыслу, а не по точным словам |

#### `tooltip.richTextToggleQuestion`
| Lang | Translation |
|------|-------------|
| en | Switch to rich text to add bold, tables, code, and colour |
| hi | बोल्ड, टेबल, कोड और रंग जोड़ने के लिए रिच टेक्स्ट पर स्विच करें |
| ta | தடிமன், அட்டவணைகள், குறியீடு மற்றும் வண்ணம் சேர்க்க செம உரைக்கு மாறவும் |
| te | బోల్డ్, టేబుల్స్, కోడ్ మరియు రంగు జోడించడానికి రిచ్ టెక్స్ట్‌కు మారండి |
| ka | ಬೋಲ್ಡ್, ಟೇಬಲ್, ಕೋಡ್ ಮತ್ತು ಬಣ್ಣ ಸೇರಿಸಲು ರಿಚ್ ಟೆಕ್ಸ್ಟ್‌ಗೆ ಬದಲಾಯಿಸಿ |
| bn | বোল্ড, টেবিল, কোড এবং রঙ যোগ করতে রিচ টেক্সটে স্যুইচ করুন |
| gu | બોલ્ડ, ટેબલ, કોડ અને રંગ ઉમેરવા રિચ ટેક્સ્ટ પર સ્વિચ કરો |
| es | Cambia a texto enriquecido para añadir negrita, tablas, código y color |
| fr | Passer au texte enrichi pour ajouter gras, tableaux, code et couleur |
| de | Zu Rich Text wechseln, um Fett, Tabellen, Code und Farbe hinzuzufügen |
| ru | Переключитесь на расширенный текст для добавления жирного, таблиц, кода и цвета |

#### `tooltip.richTextToggleOptions`
| Lang | Translation |
|------|-------------|
| en | Format answer options with bold, italic, and other styles |
| hi | उत्तर विकल्पों को बोल्ड, इटैलिक और अन्य शैलियों से स्वरूपित करें |
| ta | பதில் விருப்பங்களை தடிமன், சாய்வு மற்றும் பிற நடைகளில் வடிவமைக்கவும் |
| te | సమాధాన ఎంపికలను బోల్డ్, ఇటాలిక్ మరియు ఇతర స్టైల్స్‌తో ఫార్మాట్ చేయండి |
| ka | ಉತ್ತರ ಆಯ್ಕೆಗಳನ್ನು ಬೋಲ್ಡ್, ಇಟಾಲಿಕ್ ಮತ್ತು ಇತರ ಶೈಲಿಗಳಲ್ಲಿ ಫಾರ್ಮ್ಯಾಟ್ ಮಾಡಿ |
| bn | উত্তর বিকল্পগুলিকে বোল্ড, ইটালিক এবং অন্যান্য স্টাইলে ফর্ম্যাট করুন |
| gu | જવાબ વિકલ્પોને બોલ્ડ, ઇટાલિક અને અન્ય સ્ટાઇલ સાથે ફોર્મેટ કરો |
| es | Dar formato a las opciones de respuesta con negrita, cursiva y otros estilos |
| fr | Mettre en forme les options de réponse avec gras, italique et autres styles |
| de | Antwortoptionen mit Fett, Kursiv und anderen Stilen formatieren |
| ru | Форматируйте варианты ответов жирным, курсивом и другими стилями |

#### `tooltip.scaleCorrectAnswer`
| Lang | Translation |
|------|-------------|
| en | The scale value (1–5) that will be marked as correct |
| hi | स्केल मान (1–5) जिसे सही के रूप में चिह्नित किया जाएगा |
| ta | சரியான என்று குறிக்கப்படும் அளவு மதிப்பு (1–5) |
| te | సరైనదిగా గుర్తించబడే స్కేల్ విలువ (1–5) |
| ka | ಸರಿ ಎಂದು ಗುರುತಿಸಲಾಗುವ ಸ್ಕೇಲ್ ಮೌಲ್ಯ (1–5) |
| bn | স্কেল মান (1–5) যা সঠিক হিসেবে চিহ্নিত হবে |
| gu | સ્કેલ મૂલ્ય (1–5) જે સાચા તરીકે ચિહ્નિત કરવામાં આવશે |
| es | El valor de escala (1–5) que se marcará como correcto |
| fr | La valeur de l'échelle (1–5) qui sera marquée comme correcte |
| de | Der Skalenwert (1–5), der als richtig markiert wird |
| ru | Значение шкалы (1–5), которое будет отмечено как правильное |

#### `tooltip.revealAnswer`
| Lang | Translation |
|------|-------------|
| en | Show participants which answer was correct |
| hi | प्रतिभागियों को दिखाएं कि कौन सा उत्तर सही था |
| ta | பங்கேற்பாளர்களுக்கு எந்த பதில் சரியானது என்று காட்டவும் |
| te | పాల్గొనేవారికి ఏ సమాధానం సరైనదో చూపించండి |
| ka | ಭಾಗವಹಿಸುವವರಿಗೆ ಯಾವ ಉತ್ತರ ಸರಿ ಎಂದು ತೋರಿಸಿ |
| bn | অংশগ্রহণকারীদের দেখান কোন উত্তরটি সঠিক ছিল |
| gu | સહભાગીઓને બતાવો કે કઈ જવાબ સાચો હતો |
| es | Mostrar a los participantes qué respuesta era correcta |
| fr | Montrer aux participants quelle réponse était correcte |
| de | Teilnehmern zeigen, welche Antwort richtig war |
| ru | Показать участникам, какой ответ был правильным |

#### `tooltip.sessionCode`
| Lang | Translation |
|------|-------------|
| en | Share this code — participants go to swaya.me and enter it to join |
| hi | यह कोड साझा करें — प्रतिभागी swaya.me पर जाकर इसे दर्ज करके जुड़ते हैं |
| ta | இந்த குறியீட்டை பகிரவும் — பங்கேற்பாளர்கள் swaya.me க்கு சென்று அதை உள்ளிட்டு சேருவார்கள் |
| te | ఈ కోడ్ పంచుకోండి — పాల్గొనేవారు swaya.me కి వెళ్లి దీన్ని నమోదు చేసి చేరుతారు |
| ka | ಈ ಕೋಡ್ ಹಂಚಿಕೊಳ್ಳಿ — ಭಾಗವಹಿಸುವವರು swaya.me ಗೆ ಹೋಗಿ ಅದನ್ನು ನಮೂದಿಸಿ ಸೇರುತ್ತಾರೆ |
| bn | এই কোড শেয়ার করুন — অংশগ্রহণকারীরা swaya.me তে গিয়ে এটি প্রবেশ করে যোগ দেয় |
| gu | આ કોડ શેર કરો — સહભાગીઓ swaya.me પર જઈ તે દાખલ કરીને જોડાય છે |
| es | Comparte este código — los participantes van a swaya.me y lo introducen para unirse |
| fr | Partagez ce code — les participants se rendent sur swaya.me et le saisissent pour rejoindre |
| de | Diesen Code teilen — Teilnehmer gehen zu swaya.me und geben ihn ein, um beizutreten |
| ru | Поделитесь этим кодом — участники идут на swaya.me и вводят его для присоединения |

#### `tooltip.stopQuiz`
| Lang | Translation |
|------|-------------|
| en | End the live session. Results are saved and available in History. |
| hi | लाइव सत्र समाप्त करें। परिणाम सहेजे जाते हैं और इतिहास में उपलब्ध होते हैं। |
| ta | நேரடி அமர்வை முடிக்கவும். முடிவுகள் சேமிக்கப்பட்டு வரலாற்றில் கிடைக்கும். |
| te | లైవ్ సెషన్ ముగించండి. ఫలితాలు సేవ్ చేయబడి చరిత్రలో అందుబాటులో ఉంటాయి. |
| ka | ಲೈವ್ ಸೆಷನ್ ಮುಗಿಸಿ. ಫಲಿತಾಂಶಗಳು ಉಳಿಸಲ್ಪಟ್ಟು ಇತಿಹಾಸದಲ್ಲಿ ಲಭ್ಯವಿರುತ್ತವೆ. |
| bn | লাইভ সেশন শেষ করুন। ফলাফল সংরক্ষিত এবং ইতিহাসে পাওয়া যাবে। |
| gu | લાઇવ સત્ર સમાપ્ત કરો. પરિણામો સાચવવામાં આવ્યા છે અને ઇતિહાસમાં ઉપલબ્ધ છે. |
| es | Finalizar la sesión en vivo. Los resultados se guardan y están disponibles en Historial. |
| fr | Terminer la session en direct. Les résultats sont sauvegardés et disponibles dans l'Historique. |
| de | Live-Sitzung beenden. Ergebnisse werden gespeichert und sind im Verlauf verfügbar. |
| ru | Завершить живую сессию. Результаты сохраняются и доступны в Истории. |

---

### Empty state guidance keys

#### `tooltip.emptyStateTitle`
| Lang | Translation |
|------|-------------|
| en | Create your first quiz |
| hi | अपनी पहली क्विज़ बनाएं |
| ta | உங்கள் முதல் வினாடி வினாவை உருவாக்கவும் |
| te | మీ మొదటి క్విజ్ సృష్టించండి |
| ka | ನಿಮ್ಮ ಮೊದಲ ರಸಪ್ರಶ್ನೆ ರಚಿಸಿ |
| bn | আপনার প্রথম কুইজ তৈরি করুন |
| gu | તમારી પ્રથમ ક્વિઝ બનાવો |
| es | Crea tu primer cuestionario |
| fr | Créez votre premier quiz |
| de | Erstellen Sie Ihr erstes Quiz |
| ru | Создайте свою первую викторину |

#### `tooltip.emptyStateSubtitle`
| Lang | Translation |
|------|-------------|
| en | Choose the type that fits your use case |
| hi | अपने उपयोग के अनुसार प्रकार चुनें |
| ta | உங்கள் பயன்பாட்டிற்கு பொருந்தும் வகையை தேர்ந்தெடுக்கவும் |
| te | మీ వినియోగ సందర్భానికి సరిపోయే రకాన్ని ఎంచుకోండి |
| ka | ನಿಮ್ಮ ಬಳಕೆಯ ಸಂದರ್ಭಕ್ಕೆ ಸೂಕ್ತವಾದ ಪ್ರಕಾರ ಆರಿಸಿ |
| bn | আপনার ব্যবহারের ক্ষেত্রে উপযুক্ত ধরন বেছে নিন |
| gu | તમારા ઉપયોગ માટે યોગ્ય પ્રકાર પસંદ કરો |
| es | Elige el tipo que se adapta a tu caso de uso |
| fr | Choisissez le type qui correspond à votre cas d'utilisation |
| de | Wählen Sie den Typ, der zu Ihrem Anwendungsfall passt |
| ru | Выберите тип, подходящий для вашего случая |

#### `tooltip.emptyStateQuizDesc`
| Lang | Translation |
|------|-------------|
| en | Live Quiz — run with an audience in real time |
| hi | लाइव क्विज़ — दर्शकों के साथ रियल टाइम में चलाएं |
| ta | நேரடி வினாடி வினா — பார்வையாளர்களுடன் நிகழ்நேரத்தில் நடத்தவும் |
| te | లైవ్ క్విజ్ — ప్రేక్షకులతో రియల్ టైమ్‌లో నడపండి |
| ka | ಲೈವ್ ರಸಪ್ರಶ್ನೆ — ಪ್ರೇಕ್ಷಕರೊಂದಿಗೆ ನೈಜ ಸಮಯದಲ್ಲಿ ನಡೆಸಿ |
| bn | লাইভ কুইজ — দর্শকদের সাথে রিয়েল টাইমে পরিচালনা করুন |
| gu | લાઇવ ક્વિઝ — પ્રેક્ષકો સાથે રીઅલ ટાઇમમાં ચલાવો |
| es | Quiz en vivo — ejecuta con una audiencia en tiempo real |
| fr | Quiz en direct — lancez avec une audience en temps réel |
| de | Live-Quiz — mit einem Publikum in Echtzeit durchführen |
| ru | Живая викторина — проведите с аудиторией в реальном времени |

#### `tooltip.emptyStatePollDesc`
| Lang | Translation |
|------|-------------|
| en | Live Poll — gather instant audience responses |
| hi | लाइव पोल — दर्शकों की तत्काल प्रतिक्रियाएं एकत्र करें |
| ta | நேரடி வாக்கெடுப்பு — உடனடி பார்வையாளர் பதில்களை சேகரிக்கவும் |
| te | లైవ్ పోల్ — తక్షణ ప్రేక్షక ప్రతిస్పందనలు సేకరించండి |
| ka | ಲೈವ್ ಪೋಲ್ — ತಕ್ಷಣದ ಪ್ರೇಕ್ಷಕ ಪ್ರತಿಕ್ರಿಯೆಗಳನ್ನು ಸಂಗ್ರಹಿಸಿ |
| bn | লাইভ পোল — তাৎক্ষণিক দর্শকদের প্রতিক্রিয়া সংগ্রহ করুন |
| gu | લાઇવ પોલ — તત્કાળ પ્રેક્ષક પ્રતિક્રિયાઓ એકત્ર કરો |
| es | Encuesta en vivo — recopila respuestas instantáneas de la audiencia |
| fr | Sondage en direct — recueillez des réponses instantanées de votre audience |
| de | Live-Umfrage — sofortige Publikumsantworten sammeln |
| ru | Живой опрос — собирайте мгновенные ответы аудитории |

#### `tooltip.emptyStateOfflinePollDesc`
| Lang | Translation |
|------|-------------|
| en | Offline Poll — share a link, collect responses anytime |
| hi | ऑफलाइन पोल — लिंक साझा करें, कभी भी प्रतिक्रियाएं एकत्र करें |
| ta | ஆஃப்லைன் வாக்கெடுப்பு — இணைப்பை பகிரவும், எப்போது வேண்டுமானாலும் பதில்களை சேகரிக்கவும் |
| te | ఆఫ్‌లైన్ పోల్ — లింక్ పంచుకోండి, ఎప్పుడైనా ప్రతిస్పందనలు సేకరించండి |
| ka | ಆಫ್‌ಲೈನ್ ಪೋಲ್ — ಲಿಂಕ್ ಹಂಚಿಕೊಳ್ಳಿ, ಯಾವಾಗ ಬೇಕಾದರೂ ಪ್ರತಿಕ್ರಿಯೆ ಸಂಗ್ರಹಿಸಿ |
| bn | অফলাইন পোল — লিঙ্ক শেয়ার করুন, যেকোনো সময় প্রতিক্রিয়া সংগ্রহ করুন |
| gu | ઑફલાઇન પૉલ — લિંક શેર કરો, ગમે ત્યારે પ્રતિક્રિયા એકત્ર કરો |
| es | Encuesta sin conexión — comparte un enlace, recoge respuestas en cualquier momento |
| fr | Sondage hors ligne — partagez un lien, collectez des réponses à tout moment |
| de | Offline-Umfrage — Link teilen, Antworten jederzeit sammeln |
| ru | Офлайн-опрос — поделитесь ссылкой, собирайте ответы в любое время |

#### `tooltip.emptyStateExamDesc`
| Lang | Translation |
|------|-------------|
| en | Test / Exam — timed, auto-scored, shareable via link |
| hi | टेस्ट / परीक्षा — समयबद्ध, स्वतः-स्कोर, लिंक के माध्यम से साझा करने योग्य |
| ta | சோதனை / தேர்வு — நேரம் வரையறுக்கப்பட்ட, தானியங்கி மதிப்பீடு, இணைப்பு மூலம் பகிரக்கூடியது |
| te | టెస్ట్ / పరీక్ష — సమయ పరిమితి, స్వయంచాలిత స్కోరింగ్, లింక్ ద్వారా పంచుకోదగినది |
| ka | ಟೆಸ್ಟ್ / ಪರೀಕ್ಷೆ — ಸಮಯ ನಿರ್ಬಂಧ, ಸ್ವಯಂ-ಅಂಕ, ಲಿಂಕ್ ಮೂಲಕ ಹಂಚಿಕೊಳ್ಳಬಹುದು |
| bn | টেস্ট / পরীক্ষা — সময়বদ্ধ, স্বয়ংক্রিয় স্কোর, লিঙ্কের মাধ্যমে শেয়ারযোগ্য |
| gu | ટેસ્ટ / પરીક્ષા — સમય-મર્યાદિત, ઑટો-સ્કોર, લિંક દ્વારા શેર કરી શકાય |
| es | Test / Examen — con tiempo, puntuación automática, compartible por enlace |
| fr | Test / Examen — chronométré, noté automatiquement, partageable par lien |
| de | Test / Prüfung — zeitgesteuert, automatisch bewertet, per Link teilbar |
| ru | Тест / Экзамен — с таймером, автооценкой, доступен по ссылке |

---

## Implementation Plan

### Step 1 — Add `tooltip` namespace to all 11 locale files

**Files:** `frontend/src/locales/{en,hi,ta,te,ka,bn,gu,es,fr,de,ru}/translation.json`

Add a new `"tooltip": { ... }` top-level key to each file with all 19 tooltip keys listed in the translations above.

---

### Step 2 — Header tooltips (H1, H2, H3)

**File:** `frontend/src/App.jsx`

Wrap the theme toggle button, language switcher, and logout button in `<Tooltip title={t('tooltip.themeToggle')}>` etc. These are currently icon-only buttons with no label.

---

### Step 3 — Dashboard tooltips (D1–D5)

**File:** `frontend/src/features/dashboard/Dashboard.jsx`

- **D1** (Use Template): wrap existing `<Button>` in `<Tooltip>`
- **D2/D3** (Star icon): conditional tooltip — `t('tooltip.makeTemplate')` when not template, `t('tooltip.removeTemplate')` when already template
- **D4** (History): wrap existing `<Button icon={<HistoryOutlined/>}>` in `<Tooltip>`
- **D5** (Start Quiz): wrap existing `<Button type="primary" icon={<PlayCircleOutlined/>}>` in `<Tooltip>`

---

### Step 4 — Update existing info icon copy (D6–D9)

**File:** `frontend/src/locales/{all 11}/translation.json`

Update copy for `quiz.quizTypeInfo`, `quiz.pollTypeInfo`, `offlinePoll.typeInfo`, `exam.typeInfo` to the improved wording in this plan.

---

### Step 5 — Quiz Builder tooltips + inline hints (B1–B10)

**File:** `frontend/src/features/quiz/QuizBuilder.jsx`

- **B1, B2** (Publish/Unpublish): add `<Tooltip>` wrappers
- **B3** (Copy Link): add `<Tooltip>` wrapper
- **B4–B7** (Points, Max Time, Negative Points, Expected Answer): add `help={t('tooltip.xxx')}` prop to the relevant `<Form.Item>` — renders as small grey text below the input
- **B8, B9** (Rich text toggles): add `<Tooltip>` wrappers on the toggle `<Button>` elements
- **B10** (Scale correct answer): add `help=` on the `<Form.Item>`

---

### Step 6 — Quiz Control tooltips (C1, C2, C4)

**File:** `frontend/src/features/quiz/QuizControl.jsx`

- **C1** (Reveal Answer): add `<Tooltip>` wrapper
- **C2** (Session code): add `help={t('tooltip.sessionCode')}` on the `<Form.Item>` or as a `<Typography.Text type="secondary">` below the copyable input
- **C4** (Stop Quiz): add `<Tooltip>` wrapper on the Popconfirm trigger button

---

### Step 7 — Empty state guidance card (Dashboard)

**File:** `frontend/src/features/dashboard/Dashboard.jsx`

Replace `<Empty description="No quizzes found" />` with a custom card component showing the 4 quiz types with their `tooltip.emptyState*` descriptions and a "Create" button per type. Only shown when the quiz list is empty AND no search/folder filter is active.

---

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/locales/*/translation.json` (×11) | Add `tooltip` namespace with 19 keys; update 4 existing info-icon strings |
| `frontend/src/App.jsx` | Wrap header icon buttons in `<Tooltip>` |
| `frontend/src/features/dashboard/Dashboard.jsx` | Wrap 5 buttons in `<Tooltip>`; replace empty state |
| `frontend/src/features/quiz/QuizBuilder.jsx` | 3 `<Tooltip>` wrappers + 4 `Form.Item help=` props + 2 rich-text toggle tooltips |
| `frontend/src/features/quiz/QuizControl.jsx` | 2 `<Tooltip>` wrappers + 1 inline hint |

**No backend changes. No migrations.**
