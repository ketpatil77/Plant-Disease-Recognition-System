# 🌱 Plant Disease Recognition System - UI/DOM Analysis

**Status**: Development Server Running  
**URL**: http://localhost:5000  
**Date**: April 14, 2026

---

## 📐 Architecture Overview

### Page Structure (DOM Tree)
```
html[lang="mr"][data-theme="dark"]
├── head
│   ├── meta charset="UTF-8"
│   ├── meta viewport (responsive)
│   ├── manifest.json (PWA)
│   ├── theme-color meta tag
│   ├── i18n data attributes
│   └── CSS/JS imports
├── body.app-shell
│   ├── div.app-aurora (decorative background)
│   ├── header.app-header (sticky navigation)
│   ├── div.app-body (main container)
│   │   ├── aside.app-sidebar (collapsible menu)
│   │   └── div.content-area
│   │       ├── nav.app-nav (breadcrumb)
│   │       └── main#app-content
│   └── footer (implicit)
```

---

## 🎨 Visual Design System

### Color Palette
| Token | Dark Theme | Light Theme | Usage |
|-------|-----------|------------|-------|
| `--neon-green` | `#00FF9D` | N/A | Primary accent, CTAs |
| `--sky-blue` | `#11C7FF` | `#11C7FF` | Secondary accent |
| `--soil-black` | `#0D0D0D` | N/A | Background dark |
| `--crop-yellow` | `#FFB400` | N/A | Warnings, alerts |
| `--leaf-green` | `#00C47E` | Primary | Success states |
| `--color-bg` | Dark: `#0D0D0D` | Light: `#f4f6fb` | Surface background |
| `--color-surface` | `rgba(13, 13, 13, 0.85)` | `rgba(255,255,255,0.9)` | Cards, modals |

### Typography
- **Font System**: System stack (not explicitly defined - likely sans-serif)
- **Hierarchy**: CSS uses data-i18n attributes for i18n
- **Text colors**: Primary, secondary, disabled states via CSS variables

### Spacing System
```css
--spacing-xs: 0.25rem;  /* 4px */
--spacing-sm: 0.5rem;   /* 8px */
--spacing-md: 1rem;     /* 16px */
--spacing-lg: 1.5rem;   /* 24px */
--spacing-xl: 2rem;     /* 32px */
--spacing-2xl: 2.5rem;  /* 40px */
```

### Border Radius
```css
--radius-lg: 26px;  /* Large cards, modals */
--radius-md: 18px;  /* Medium elements */
--radius-sm: 12px;  /* Small buttons, inputs */
```

### Effects
- **Glow**: `0 0 35px rgba(0, 255, 157, 0.25), 0 20px 45px rgba(0, 0, 0, 0.65)`
- **Shadow**: `0 35px 60px rgba(17, 27, 48, 0.56)`
- **Transitions**: `--transition-fast: 0.25s ease-out`

---

## 🧩 Component Inventory

### 1. **Header Component** (`.app-header`)
**Location**: `templates/base.html` lines 18-35  
**Purpose**: Main navigation bar (sticky)  
**Elements**:
- Brand block: Logo (🌱) + Title ("Agro Vision") + Tagline
- Language toggle: मराठी / EN buttons
- Theme toggle: ☀️ / 🌙 (sun/moon icons)
- Help button: "?" link
- Sidebar toggle: ☰ hamburger menu

**Accessibility**: 
- Role="group" on language selector
- aria-labels on all buttons
- i18n support via data-i18n attributes

---

### 2. **Sidebar Component** (`.app-sidebar`)
**Location**: `templates/base.html` lines 36-68  
**Purpose**: Main navigation menu (collapsible on mobile)  
**Structure**:
```
Sidebar Brand
├── Sidebar Groups (organized by <details>)
│   ├── CORE
│   │   ├── 🏠 Dashboard
│   │   ├── 📷 Scanner
│   │   ├── 📚 Disease Library
│   │   └── 🗂 My Reports (with count chip)
│   ├── ANALYTICS (placeholder)
│   ├── TOOLS (coming soon)
│   ├── PERSONAL
│   │   └── ⚙️ Settings
│   ├── HELP
│   │   ├── 🎓 Tutorials
│   │   └── ❓ Help
```

**Features**:
- Uses HTML `<details>` for expandable sections
- Count badges on "My Reports"
- Active state tracking via `.is-active` class
- Icon + text labels for accessibility

---

### 3. **Dashboard Layout** (`.dashboard-wrapper`)
**Location**: `templates/home.html` lines 2-150  
**Purpose**: Homepage hero + key actions + analytics overview  

#### Left Column (Primary Content)
1. **Hero Card** (`.hero-card`)
   - Icon: 🌾
   - Call-to-action text
   - Voice command button (🎙)
   - Offline capability indicator

2. **Action Card** (`.action-card`)
   - Buttons: 📷 Camera Scan | 🖼 Upload Photo
   - Progress bar for analysis
   - i18n labels

3. **Alert Card** (`.intel-card`)
   - Local weather alerts
   - Fungal risk indicators
   - Real-time weather data display

4. **Reports Card** (`.reports-card`)
   - Skeleton loader (shimmer effect)
   - Recent reports list
   - Crop name, disease, timestamp
   - Link to full report view
   - Empty state message

#### Right Column (Analytics + Insights)
1. **Disease Forecast Card** (`.forecast-card`)
   - 3-day risk prediction
   - Icons: 🍄 (fungal) | 🦠 (bacterial) | 🐛 (pest) | 🌾 (low)
   - Risk level indicators
   - Temperature/Humidity/Rain data attributes

2. **Weather Card** (`.weather-card`)
   - Current conditions table
   - Risk badge (low/medium/high)
   - Temperature, Humidity, Rain, Tip
   - Offline indicator

3. **Market Price Card** (`.market-card`)
   - District selector dropdown
   - Price table with crop names
   - Trend indicators: ▲ (up) | ▼ (down) | • (stable)
   - Skeleton loader

---

## 📱 Responsive Behavior

### Key Classes
- `.app-body` - Main flex container
- `.dashboard-wrapper` - Two-column grid
- `.dashboard-column` - Left (primary) and right (analytics)
- `.sidebar-toggle` - Hidden on desktop, visible on mobile
- `.app-sidebar` - Collapses/expands via JavaScript

### Breakpoints (Implied)
- **Mobile**: Sidebar as offcanvas/drawer
- **Desktop**: Sidebar always visible, 2-column dashboard
- **Viewport**: `meta name="viewport" content="width=device-width, initial-scale=1"`

---

## 🎯 Key Interactive Elements

### Buttons & CTAs
```html
<!-- Primary CTA -->
<a class="pill primary" href="...">
  <span>📷</span> Camera Scan
</a>

<!-- Secondary -->
<a class="pill secondary" href="...">
  <span>🖼</span> Photo Upload
</a>

<!-- Ghost/Tertiary -->
<a class="ghost" href="...">View All</a>

<!-- Icon Button -->
<button class="icon-btn" data-theme-toggle>
  <span>☀️</span> / <span>🌙</span>
</button>
```

### Interactive Features (JS)
1. **Theme Toggle** (`js/theme.js`)
   - Dark ↔ Light mode
   - Persisted in localStorage: `agro-theme`
   
2. **Language Toggle** (`js/language.js`)
   - मराठी ↔ EN
   - Attribute: `data-i18n="..."` for translation keys
   
3. **Voice Commands** (`js/voice.js`)
   - 🎙 button activation
   - Mic status indicator
   
4. **Sidebar Mobile** (`js/ui-sound.js`, DOM events)
   - Toggle sidebar on hamburger click
   - Smooth transitions

5. **Sound Effects** (`js/ui-sound.js`)
   - Hover sounds: `data-hover-sound`
   - Interactive feedback

6. **Offline Support** (`js/offline.js`)
   - Service worker integration (`sw.js`)
   - Cached data fallback
   - Offline indicators

---

## 🔄 Data Flow & State Management

### Template Variables Passed
```python
# From app.py route handlers:
- active_page: str (for nav highlighting)
- reports: list (recent predictions)
- weather: dict (current conditions)
- forecast: list (3-day forecast)
- market: list (price data)
- districts: list (region selection)
- selected_district: str (current filter)
```

### Dynamic Content
- **Skeleton loaders** on data-heavy cards (`.skeleton-card`)
- **Empty states** when data unavailable (`data-i18n="..."`)
- **Conditional rendering** via Jinja2 `{% if %}` blocks

---

## ♿ Accessibility Features

### ARIA & Semantics
- `role="group"` on language selector
- `aria-label="..."` on icon buttons
- `aria-hidden="true"` on decorative elements (🌱, emojis)
- `aria-labelledby="..."` on content sections
- Semantic HTML: `<header>`, `<aside>`, `<article>`, `<nav>`

### Internationalization (i18n)
- All user-facing text via `data-i18n="..."` attributes
- Language files: `/static/lang/eng.json`, `/static/lang/mar.json`
- Key structure: `app.title`, `nav.home`, `home.hero.title`, etc.

### Keyboard Navigation
- Tab through sidebar links
- Collapsible `<details>` elements
- Button focus states (implied)

---

## 📦 Static Assets

### CSS
- **Main**: `static/css/main.css` (comprehensive design system)

### JavaScript (Modular)
- `js/theme.js` - Theme persistence & switching
- `js/language.js` - i18n initialization & switching
- `js/camera.js` - Camera input handling
- `js/voice.js` - Voice command recognition
- `js/offline.js` - Offline fallback logic
- `js/ui-sound.js` - Hover/interaction sounds
- `js/history.js` - Report history management
- `js/trends.js` - Analytics visualization
- `js/forecast.js` - Disease forecast rendering

### Icons
- `static/icons/` - PNG icon assets (app icons, favicons)

### Language Files
- `static/lang/eng.json` - English translations
- `static/lang/mar.json` - Marathi translations

### Data
- `static/data/trends.json` - Analytics data cache

---

## 🚀 Performance Observations

### Optimization Strategies
1. **Lazy Loading**: Skeleton placeholders for async data
2. **CSS Variables**: Efficient theme switching (no reload)
3. **PWA Support**: Service worker caching (`sw.js`)
4. **Offline-First**: Local data cache via `localStorage`
5. **Module Structure**: Separate JS files (code splitting)
6. **Glow Effects**: GPU-accelerated shadows & glows

### Asset Size Impact
- Color palette: 25+ CSS variables (minimal footprint)
- Emojis: Direct Unicode (no image bloat)
- Fonts: System stack (no web fonts loaded)

---

## 🐛 Potential UI Issues/Improvements

### Current Observations
1. ✅ Theme system working (dark/light mode icons visible)
2. ✅ Sidebar structure complete (mobile-ready)
3. ✅ i18n hooks in place (Marathi primary language)
4. ✅ Voice command integration started
5. ⚠️ Market card dropdown - needs styling verification
6. ⚠️ Skeleton loaders - check shimmer animation CSS
7. ⚠️ Forecast icons - emoji rendering on all browsers?

### Recommendations
| Priority | Issue | Suggested Fix |
|----------|-------|---------------|
| High | Focus states | Add `:focus-visible` outline to all buttons |
| High | Touch targets | Ensure 44px min height on mobile buttons |
| Medium | Color contrast | Verify WCAG AA compliance on secondary text |
| Medium | Loading states | Add aria-busy="true" on data-loading cards |
| Low | Emoji fallback | Add text fallback for older browsers |
| Low | Animation perf | Test GPU acceleration on large screens |

---

## 📋 Navigation Sitemap

```
/ (Dashboard/Home)
├── /scanner?mode=camera (Camera Scan)
├── /scanner?mode=upload (Upload Photo)
├── /disease-library (Disease Reference)
├── /history (My Reports)
├── /prediction (Prediction Results)
├── /scan-tutorial (Tutorial)
├── /settings (Settings & Help)
│   └── #help (Help section anchor)
└── /trending (Trends - coming soon)
```

---

## 💾 Data Storage

### Backend Models
- **Reports**: `crop`, `disease`, `created_at`, `image_path`
- **Weather**: `temperature`, `humidity`, `rain`, `risk`, `tip`
- **Market**: `crop`, `price`, `trend`, `district`
- **Forecast**: `day`, `category`, `level`, `temperature`, `humidity`, `rain_chance`

### Frontend Cache (localStorage)
- `agro-theme` - User's preferred theme

### Service Worker Cache (sw.js)
- Static assets, templates, offline fallback page

---

## 🎓 Development Notes

### File Structure
```
Plant-Disease-Recognition-System/
├── app.py (Flask routes)
├── backend/
│   ├── inference.py (Model prediction)
│   ├── model.py (Model loading)
│   └── metadata.py (Constants)
├── templates/
│   ├── base.html (Layout)
│   ├── home.html (Dashboard)
│   ├── scanner.html (Photo capture)
│   ├── prediction.html (Results)
│   └── [other pages]
├── static/
│   ├── css/main.css (Styles)
│   ├── js/ (Modular scripts)
│   ├── lang/ (i18n files)
│   ├── data/ (Cache)
│   └── icons/ (Assets)
└── manifest.json (PWA metadata)
```

### Key Technical Decisions
1. **Flexbox + CSS Grid** - Modern layout system
2. **CSS Variables** - Dynamic theming without JS
3. **Data Attributes** - Semantic markup (data-i18n, data-theme)
4. **Emojis** - Lightweight icon system (vs SVG/Font)
5. **Service Worker** - Offline-first PWA architecture
6. **Jinja2 Templates** - Server-side rendering with i18n hooks

---

## ✅ Checklist for Testing

- [ ] Theme toggle works (CSS variables update)
- [ ] Language toggle updates all i18n attributes
- [ ] Sidebar responsive on mobile (hamburger menu)
- [ ] Voice button accessible and functional
- [ ] Voice status indicator updates real-time
- [ ] Report list renders with correct data
- [ ] Forecast icons display correctly
- [ ] Market dropdown filters by district
- [ ] Risk badges show correct color coding
- [ ] Offline indicator appears when needed
- [ ] All links navigate to correct routes
- [ ] Keyboard tab order is logical
- [ ] Screen reader announces all content
- [ ] Colors meet WCAG AA contrast ratios

---

**Analysis Generated**: 2026-04-14  
**Status**: Ready for QA Testing  
**Next Steps**: Chrome DevTools inspection of live app at http://localhost:5000
