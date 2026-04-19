const keywordLibrary = [
  {
    label: { en: 'Blight', mr: 'ब्लाइट' },
    keywords: ['blight', 'ब्लाइट', 'लेट ब्लाइट', 'बलेट'],
    remedyHint: {
      en: 'For blight, remove infected leaves and use a suitable copper-based fungicide.',
      mr: 'ब्लाइटसाठी संक्रमित पाने काढा आणि योग्य कॉपर-आधारित बुरशीनाशक वापरा.',
    },
  },
  {
    label: { en: 'Rust', mr: 'रस्ट' },
    keywords: ['rust', 'रस्ट'],
    remedyHint: {
      en: 'For rust, start early leaf monitoring and use neem-based or recommended protective spray.',
      mr: 'रस्टसाठी पानांचे लवकर निरीक्षण करा आणि नीम-आधारित किंवा शिफारस केलेली फवारणी वापरा.',
    },
  },
  {
    label: { en: 'Mildew', mr: 'मिल्ड्यू' },
    keywords: ['mildew', 'मिल्ड्यू', 'पावडरी'],
    remedyHint: {
      en: 'For mildew, improve airflow and use a neem-based or recommended mildew treatment.',
      mr: 'मिल्ड्यूसाठी हवेचा प्रवाह वाढवा आणि नीम-आधारित किंवा शिफारस केलेली उपाययोजना वापरा.',
    },
  },
];

function detectKeyword(text) {
  if (!text) return null;
  const normalized = text.toLowerCase();
  return keywordLibrary.find((entry) => entry.keywords.some((term) => normalized.includes(term)));
}

function speakText(text, lang) {
  if (!window.speechSynthesis || !text) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang || document.documentElement.lang || 'mr-IN';
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

function localizedKeywordLabel(keyword) {
  const lang = window.getCurrentLang?.() || 'mr';
  if (!keyword?.label) return '';
  return keyword.label[lang] || keyword.label.mr || keyword.label.en || '';
}

function localizedRemedyHint(keyword) {
  const lang = window.getCurrentLang?.() || 'mr';
  if (!keyword?.remedyHint) return '';
  return keyword.remedyHint[lang] || keyword.remedyHint.mr || keyword.remedyHint.en || '';
}

// Helper function to get translated text
async function getTranslation(key) {
  if (typeof window.getTranslation === 'function') {
    return window.getTranslation(key);
  }
  const lang = window.getCurrentLang?.() || localStorage.getItem('agro-lang') || 'mr';
  const langFile = lang === 'en' ? 'eng' : 'mar';
  
  try {
    const res = await fetch(`/static/lang/${langFile}.json`);
    if (!res.ok) throw new Error('Failed to fetch');
    const dict = await res.json();
    return dict[key] || key;
  } catch (err) {
    console.error('Translation fetch failed', err);
    return key;
  }
}

function initVoiceAssistant({
  buttonSelector,
  fallbackText = 'उपलब्ध उपाय सुमारे येईल.',
  fallbackKey = '',
  onResult,
  getRemedy,
}) {
  const button = document.querySelector(buttonSelector);
  if (!button) return;
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    button.disabled = true;
    getTranslation('voice.unavailable').then(text => {
      button.title = text;
      button.setAttribute('aria-label', text);
    });
    return;
  }
  const recognition = new SpeechRecognition();
  const syncRecognitionLanguage = () => {
    const lang = window.getCurrentLang?.() || document.documentElement.lang || 'mr';
    recognition.lang = lang === 'en' ? 'en-US' : 'mr-IN';
  };
  syncRecognitionLanguage();
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  const updateState = (listening) => {
    button.dataset.listening = listening ? 'true' : 'false';
  };

  button.addEventListener('click', () => {
    if (button.dataset.listening === 'true') {
      recognition.stop();
      return;
    }
    syncRecognitionLanguage();
    recognition.start();
  });

  recognition.addEventListener('start', () => {
    updateState(true);
    if (window.showToast) {
      getTranslation('voice.listening').then(text => {
        window.showToast('info', text);
      });
    }
  });
  recognition.addEventListener('end', () => {
    updateState(false);
  });
  recognition.addEventListener('result', async (event) => {
    const transcript = event.results[0][0].transcript;
    const keyword = detectKeyword(transcript);
    const remedyFromDom = getRemedy ? getRemedy() : null;
    const translatedFallback = fallbackKey ? await getTranslation(fallbackKey) : fallbackText;
    const remedy = localizedRemedyHint(keyword) || remedyFromDom || translatedFallback;
    if (onResult) {
      onResult({ transcript, remedy, keyword });
    }
    speakText(remedy, recognition.lang);
    if (window.showToast) {
      getTranslation(keyword ? 'voice.remedy_found' : 'voice.remedy_shown').then(text => {
        const message = keyword ? `${localizedKeywordLabel(keyword)} ${text}` : text;
        window.showToast('success', message);
      });
    }
  });
  recognition.addEventListener('error', () => {
    updateState(false);
    if (window.showToast) {
      getTranslation('voice.failed').then(text => {
        window.showToast('error', text);
      });
    }
  });

  document.addEventListener('agro:languagechange', syncRecognitionLanguage);
}

export { initVoiceAssistant };
