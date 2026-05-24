"""ui.qt_main.lang — v2.992.beta-5 F13: 다국어 지원 (한국어 / English).

간단한 dict 기반 i18n. gettext 보다 가볍고 즉시 적용 가능.

사용:
    from .lang import tr, set_language
    set_language("en")   # 또는 "ko"
    btn.setText(tr("APPLY"))

키 (KEY) 는 영문 대문자 + UPPER_SNAKE_CASE.
번역 누락 시 키 자체를 반환.

설정 영구화: settings.json 의 "language" 필드 (load: _load_settings, save: _save_settings).
"""

import logging
_LOG = logging.getLogger("stl_analyzer.lang")

# 현재 언어 — "ko" (기본) 또는 "en"
_current_lang = "ko"


# ──────────────────────────────────────────────────────────
# 번역 dictionary
# ──────────────────────────────────────────────────────────
_STRINGS = {
    # ── 메뉴 ──
    "MENU_FILE":    {"ko": "&File",    "en": "&File"},
    "MENU_EDIT":    {"ko": "&Edit",    "en": "&Edit"},
    "MENU_TOOLS":   {"ko": "&Tools",   "en": "&Tools"},
    "MENU_MATERIAL":{"ko": "&Material","en": "&Material"},
    "MENU_HELP":    {"ko": "&Help",    "en": "&Help"},
    "MENU_LANGUAGE":{"ko": "언어 / Language", "en": "Language"},

    # ── File 메뉴 ──
    "FILE_OPEN":    {"ko": "열기 (Ctrl+O)",          "en": "Open (Ctrl+O)"},
    "FILE_RELOAD":  {"ko": "리로드",                  "en": "Reload"},
    "FILE_RECENT":  {"ko": "📂 최근 파일",             "en": "📂 Recent files"},
    "FILE_RECENT_NONE":{"ko": "(없음)",               "en": "(none)"},
    "FILE_RECENT_CLEAR":{"ko": "최근 파일 비우기",     "en": "Clear recent files"},
    "FILE_SAVE_STL":{"ko": "STL 저장 (Ctrl+S)",       "en": "Save STL (Ctrl+S)"},
    "FILE_SAVE_SUPPORT":{"ko": "Support STL 저장 (Ctrl+Shift+S)",
                          "en": "Save Support STL (Ctrl+Shift+S)"},
    "FILE_SAVE_REPORT":{"ko": "📄 분석 보고서 저장 (Ctrl+Shift+R)",
                         "en": "📄 Save Analysis Report (Ctrl+Shift+R)"},
    "FILE_SAVE_SCREENSHOT":{"ko": "📷 3D 뷰 스크린샷 저장 (Ctrl+Shift+P)",
                             "en": "📷 Save 3D View Screenshot (Ctrl+Shift+P)"},
    "FILE_QUIT":    {"ko": "종료 (Ctrl+W)",           "en": "Quit (Ctrl+W)"},

    # ── Edit 메뉴 ──
    "EDIT_UNDO":    {"ko": "실행 취소 (Ctrl+Z)",      "en": "Undo (Ctrl+Z)"},
    "EDIT_REDO":    {"ko": "다시 실행 (Ctrl+Y)",      "en": "Redo (Ctrl+Y)"},
    "EDIT_UNDO_OP":     {"ko": "실행 취소: {op} (Ctrl+Z)",
                          "en": "Undo: {op} (Ctrl+Z)"},
    "EDIT_REDO_OP":     {"ko": "다시 실행: {op} (Ctrl+Y)",
                          "en": "Redo: {op} (Ctrl+Y)"},
    "EDIT_CLEAR_HISTORY":{"ko": "실행 취소 기록 비우기",
                           "en": "Clear undo history"},

    # ── Tools 메뉴 ──
    "TOOLS_REANALYZE":  {"ko": "재분석 (F5)",         "en": "Re-analyze (F5)"},
    "TOOLS_FIXING":     {"ko": "고급 Fixing (F7) — 진단/Hole/Watertight 통합",
                          "en": "Advanced Fixing (F7) — Diagnose/Hole/Watertight"},
    "TOOLS_OPTIMIZE_ORIENT":{"ko": "빌드 방향 최적화",
                              "en": "Build Orientation Optimization"},
    "TOOLS_PACK":       {"ko": "다중 부품 자동 Packing (격자배치)",
                          "en": "Auto-pack Multiple Parts (Grid Layout)"},

    # ── Material / Help ──
    "MATERIAL_MDS": {"ko": "MDS 보기",                "en": "View MDS"},
    "HELP_SHORTCUTS":{"ko": "단축키 (F1)",            "en": "Shortcuts (F1)"},
    "HELP_ABOUT":   {"ko": "정보",                    "en": "About"},
    "LANG_KO":      {"ko": "한국어",                  "en": "Korean (한국어)"},
    "LANG_EN":      {"ko": "English (영어)",          "en": "English"},

    # ── 공통 버튼 ──
    "BTN_APPLY":    {"ko": "✓ 적용",                  "en": "✓ Apply"},
    "BTN_CANCEL":   {"ko": "취소",                    "en": "Cancel"},
    "BTN_CLOSE":    {"ko": "닫기",                    "en": "Close"},
    "BTN_OK":       {"ko": "확인",                    "en": "OK"},
    "BTN_YES":      {"ko": "예",                      "en": "Yes"},
    "BTN_NO":       {"ko": "아니오",                  "en": "No"},
    "BTN_RESET":    {"ko": "리셋",                    "en": "Reset"},
    "BTN_SAVE":     {"ko": "저장",                    "en": "Save"},
    "BTN_OPEN":     {"ko": "열기",                    "en": "Open"},
    "BTN_BROWSE":   {"ko": "찾아보기...",             "en": "Browse..."},

    # ── 상태바 / 액션 ──
    "STATUS_READY": {"ko": "Ready",                   "en": "Ready"},
    "STATUS_OPEN_FIRST":{"ko": "STL을 먼저 열어주세요",
                         "en": "Please open an STL first"},
    "STATUS_NO_PATH":{"ko": "파일 경로 없음",          "en": "No file path"},
    "STATUS_NO_ANALYSIS":{"ko": "분석 결과 없음 — STL 을 먼저 분석하세요",
                          "en": "No analysis result — analyze an STL first"},

    # ── 빌드 방향 / 장비 / 재료 ──
    "BUILD_DIR":    {"ko": "빌드:",                   "en": "Build:"},
    "FLIP":         {"ko": "Flip",                    "en": "Flip"},
    "MACHINE":      {"ko": "장비",                    "en": "Machine"},
    "MATERIAL":     {"ko": "재료",                    "en": "Material"},
    "EDM_MARGIN":   {"ko": "EDM마진(mm):",            "en": "EDM margin (mm):"},
    "SAFETY_FACTOR":{"ko": "안전마진:",                "en": "Safety:"},
    "PACKING":      {"ko": "패킹률(%):",              "en": "Packing (%):"},
    "QUANTITY":     {"ko": "수량:",                   "en": "Qty:"},
    "GAP":          {"ko": "Gap(mm):",                "en": "Gap (mm):"},
    "APPLY_CHANGES":{"ko": "✓ 변경사항 적용",         "en": "✓ Apply Changes"},
    "PACK_PARTS":   {"ko": "📦 격자 배치",            "en": "📦 Grid Layout"},
    "CLEAR_PACK":   {"ko": "✕ 미리보기 끄기",         "en": "✕ Clear Preview"},

    # ── 분석 결과 패널 ──
    "RESULT_TITLE": {"ko": "📊 분석 결과",            "en": "📊 Analysis Result"},
    "RESULT_OPEN_PROMPT":{"ko": "(STL 파일을 열어주세요. Ctrl+O)",
                          "en": "(Open an STL file. Ctrl+O)"},
    "GEO_TITLE":    {"ko": "[ 기하 / 메시 ]",         "en": "[ Geometry / Mesh ]"},
    "GEO_TRI":      {"ko": "삼각형      ",            "en": "Triangles   "},
    "GEO_BBOX":     {"ko": "크기 W×D×H  ",            "en": "Size W×D×H  "},
    "GEO_DIAG":     {"ko": "대각선      ",            "en": "Diagonal    "},
    "GEO_VOLUME":   {"ko": "부피        ",            "en": "Volume      "},
    "GEO_AREA":     {"ko": "표면적      ",            "en": "Surface area"},
    "GEO_AVG_TRI":  {"ko": "평균 tri 면적 ",          "en": "Avg tri area"},
    "INTEG_TITLE":  {"ko": "[ 무결성 — Magics 호환 ]",
                      "en": "[ Integrity — Magics-compatible ]"},
    "INTEG_WATERTIGHT_YES":{"ko": "✓ Watertight",     "en": "✓ Watertight"},
    "INTEG_WATERTIGHT_NO": {"ko": "✗ NOT Watertight", "en": "✗ NOT Watertight"},
    "INTEG_BAD_EDGES":{"ko": "Bad edges    ",         "en": "Bad edges    "},
    "INTEG_OPEN_EDGES":{"ko": "  ├ Open edges    ",   "en": "  ├ Open edges    "},
    "INTEG_NON_MANIFOLD":{"ko": "  └ Non-manifold ",  "en": "  └ Non-manifold "},
    "INTEG_HOLES":  {"ko": "Holes (loops)",           "en": "Holes (loops)"},
    "INTEG_SHELLS": {"ko": "Shells       ",           "en": "Shells       "},

    # ── 3D 단독창 (클립뷰) ──
    "STD_TITLE":    {"ko": "3D 단독창",               "en": "3D Standalone View"},
    "STD_CLIPPING": {"ko": "◆ Clipping",              "en": "◆ Clipping"},
    "STD_RESET_ALL":{"ko": "✕ 모두 Off",              "en": "✕ All Off"},
    "STD_OUTLINE_THICK":{"ko": "교선 두께:",          "en": "Outline thickness:"},
    "STD_MODE_OFF": {"ko": "Off",                     "en": "Off"},
    "STD_MODE_CONTOUR":{"ko": "교선",                 "en": "Contour"},
    "STD_MODE_CLIP_POS":{"ko": "Clip+",               "en": "Clip+"},
    "STD_MODE_CLIP_NEG":{"ko": "Clip−",               "en": "Clip−"},
    "STD_RENDERING":{"ko": "⚙  렌더링 중...",          "en": "⚙  Rendering..."},
    "STD_VIEW_ISO": {"ko": "◆ ISO 코너",              "en": "◆ ISO Corner"},
    "STD_VIEW_FACE":{"ko": "■ 면 (Face)",             "en": "■ Face"},
    "STD_OPEN_MULTI":{"ko": "📐 4-Pane 멀티뷰 열기",   "en": "📐 Open 4-Pane Multi View"},
    "STD_PARALLEL": {"ko": "직교",                    "en": "Orthographic"},

    # ── 단면 보기 ──
    "SLICE_TITLE":  {"ko": "단면 보기 (Cross-Section)",
                      "en": "Cross-Section View"},
    "SLICE_Z_LABEL":{"ko": "◆ Z 위치 (mm)",          "en": "◆ Z position (mm)"},
    "SLICE_STEP":   {"ko": "Step:",                   "en": "Step:"},
    "SLICE_ANIM_LOOP":{"ko": "반복",                  "en": "Loop"},
    "SLICE_ANIM_SPEED":{"ko": "속도:",                "en": "Speed:"},
    "SLICE_HATCH":  {"ko": "Hatch (45°)",             "en": "Hatch (45°)"},

    # ── 빌드 방향 score 다이얼로그 (F9) ──
    "ORIENT_TITLE": {"ko": "빌드 방향 6축 score 비교",
                      "en": "Build Orientation 6-Axis Score Comparison"},
    "ORIENT_HEADER":{"ko": "<b>임계각 {theta:.0f}° 기준</b> — 6 축 후보 metric 비교. 점수 낮을수록 좋음.",
                      "en": "<b>Threshold {theta:.0f}°</b> — Score comparison for 6 axes. Lower is better."},
    "ORIENT_BEST":  {"ko": "최적: {axis} (score {score:.2f})",
                      "en": "Best: {axis} (score {score:.2f})"},
    "ORIENT_COL_AXIS":   {"ko": "축",         "en": "Axis"},
    "ORIENT_COL_SCORE":  {"ko": "점수",       "en": "Score"},
    "ORIENT_COL_OVERHANG":{"ko": "Overhang %","en": "Overhang %"},
    "ORIENT_COL_SUPPORT":{"ko": "Support 면적 (cm²)", "en": "Support area (cm²)"},
    "ORIENT_COL_HEIGHT":{"ko": "빌드 높이 (mm)",      "en": "Build height (mm)"},
    "ORIENT_COL_CONTACT":{"ko": "Plate 접촉 (cm²)",   "en": "Plate contact (cm²)"},
    "ORIENT_COL_NTRI":   {"ko": "Overhang tri",       "en": "Overhang tri"},
    "ORIENT_APPLY_LBL":  {"ko": "<b>선택된 축으로 회전 적용:</b>",
                           "en": "<b>Apply rotation to selected axis:</b>"},

    # ── 보고서 (F2/v2.972) ──
    "REPORT_TITLE": {"ko": "분석 보고서",             "en": "Analysis Report"},
    "REPORT_NO_PATH":{"ko": "파일 경로 없음",         "en": "No file path"},
    "REPORT_SAVED": {"ko": "보고서 저장: {path}",      "en": "Report saved: {path}"},

    # ── 일반 dialog 메시지 ──
    "DLG_CLOSE_TITLE":{"ko": "종료 확인",              "en": "Confirm Close"},
    "DLG_CLOSE_BODY": {"ko": "<b>{n}개 단독창이 열려 있습니다.</b><br><br>"
                              "메인 창을 종료하면 단독창들도 함께 닫힙니다.<br>"
                              "계속 진행하시겠습니까?",
                       "en":  "<b>{n} standalone window(s) open.</b><br><br>"
                              "Closing the main window will close them too.<br>"
                              "Continue?"},

    # ── v2.992.beta-5: 탭 / 패널 / 그룹 박스 제목 ──
    "TAB_FILE_ANALYSIS":{"ko": "📁 파일 / 분석",        "en": "📁 File / Analysis"},
    "TAB_BUILD":    {"ko": "🏭 빌드·소재",            "en": "🏭 Build / Material"},
    "TAB_TRANSFORM":{"ko": "🔄 회전·스케일",          "en": "🔄 Rotate / Scale"},
    "PANEL_3D":     {"ko": "3D 미리보기",              "en": "3D Preview"},
    "PANEL_RENDER_MODE":{"ko": "렌더 모드",            "en": "Render Mode"},
    "PANEL_VIEW":   {"ko": "◆ 시점",                   "en": "◆ View"},

    # ── v2.992.beta-5: 빌드/소재 탭 라벨 ──
    "LBL_MACHINE":  {"ko": "장비:",                    "en": "Machine:"},
    "LBL_MATERIAL": {"ko": "재료:",                    "en": "Material:"},
    "LBL_DENSITY":  {"ko": "밀도:",                    "en": "Density:"},
    "LBL_BUILD_DIR":{"ko": "빌드:",                    "en": "Build:"},
    "LBL_LAYER":    {"ko": "Layer:",                   "en": "Layer:"},
    "LBL_LAYER_UM": {"ko": "Layer(μm):",               "en": "Layer (μm):"},

    # ── v2.992.beta-5: 단면 보기 라벨 ──
    "SLICE_HATCH_TITLE":{"ko": "해칭",                "en": "Hatching"},
    "SLICE_INFO":   {"ko": "단면 정보",                "en": "Section Info"},
    "MINI_VIEW":    {"ko": "Mini-view",                "en": "Mini-view"},
    "SLICE_ANIM_TITLE":{"ko": "🎞 Z 애니메이션",       "en": "🎞 Z Animation"},
    "SLICE_ANIM_FIRST":{"ko": "처음 layer (z_min)",   "en": "First layer (z_min)"},
    "SLICE_ANIM_LAST":{"ko": "마지막 layer (z_max)",  "en": "Last layer (z_max)"},
    "SLICE_ANIM_PLAY_TOOLTIP":{"ko": "재생 / 일시정지 (zoom 유지)",
                                "en": "Play / Pause (zoom preserved)"},
    "SLICE_RENDER_BTN":{"ko": "🎬 렌더",              "en": "🎬 Render"},
    "SLICE_RENDER_TOOLTIP":{"ko":
        "전체 z 범위 미리 렌더 (모든 layer 계산 + 캐시)\n"
        "→ 재생 / slider 이동 시 캐시 사용 → 실시간 부담 ↓",
        "en":
        "Pre-render all layers in Z range + cache.\n"
        "→ Playback / slider uses cache → less realtime load."},

    # ── v2.992.beta-5: 결과 패널 HTML 라벨 ──
    "RES_GEO_TITLE":{"ko": "[ 기하 / 메시 ]",         "en": "[ Geometry / Mesh ]"},
    "RES_TRIS":     {"ko": "삼각형      ",            "en": "Triangles  "},
    "RES_SIZE":     {"ko": "크기 W×D×H  ",            "en": "Size W×D×H "},
    "RES_DIAG":     {"ko": "대각선      ",            "en": "Diagonal   "},
    "RES_VOLUME":   {"ko": "부피        ",            "en": "Volume     "},
    "RES_AREA":     {"ko": "표면적      ",            "en": "Surface area"},
    "RES_AVG_TRI":  {"ko": "평균 tri 면적 ",          "en": "Avg tri area"},
    "RES_INTEG_TITLE":{"ko": "[ 무결성 — Magics 호환 ]",
                       "en": "[ Integrity — Magics-compatible ]"},
    "RES_BAD_EDGES":{"ko": "Bad edges    ",           "en": "Bad edges   "},
    "RES_OPEN_EDGES":{"ko": "  ├ Open edges    ",     "en": "  ├ Open edges    "},
    "RES_NON_MANIFOLD":{"ko": "  └ Non-manifold ",    "en": "  └ Non-manifold "},
    "RES_HOLES":    {"ko": "Holes (loops)",           "en": "Holes (loops)"},
    "RES_SHELLS":   {"ko": "Shells       ",           "en": "Shells      "},
    "RES_WT_YES":   {"ko": "✓ Watertight",            "en": "✓ Watertight"},
    "RES_WT_NO":    {"ko": "✗ NOT Watertight",        "en": "✗ NOT Watertight"},
    "RES_WT_UNCHECKED":{"ko": "— 미검사",             "en": "— Unchecked"},
    "RES_INV_NORMALS":{"ko": "Inverted normals: ",    "en": "Inverted normals: "},
    "RES_AUTO_FIXED":{"ko": "자동 보정됨",            "en": "Auto-fixed"},
    "RES_AUTO_FIX":  {"ko": "자동 수정    : ",        "en": "Auto-fix     : "},
    "RES_WARNINGS": {"ko": "경고         : ",         "en": "Warnings     : "},
    "RES_WALL_TITLE":{"ko": "[ 벽 두께 ]",            "en": "[ Wall thickness ]"},
    "RES_WALL_MIN_MED_MAX":{"ko": "min/med/max : ",   "en": "min/med/max : "},
    "RES_WALL_THIN":{"ko": "얇은벽 (≤1mm): ",         "en": "Thin walls (≤1mm): "},

    # ── v2.992.beta-5: 결과 패널 우측 (장비/재료/envelope) ──
    "RES_MACHINE_TITLE":{"ko": "[ 장비 ]",            "en": "[ Machine ]"},
    "RES_MACHINE":  {"ko": "기기        : ",          "en": "Machine     : "},
    "RES_PLATE":    {"ko": "Plate       : ",          "en": "Plate       : "},
    "RES_MAT_TITLE":{"ko": "[ 재료 / 부품 무게 ]",     "en": "[ Material / Part Weight ]"},
    "RES_MAT":      {"ko": "재료        : ",          "en": "Material    : "},
    "RES_VOL_VAL":  {"ko": "부피        : ",          "en": "Volume      : "},
    "RES_WEIGHT":   {"ko": "무게        : ",          "en": "Weight      : "},
    "RES_ENV_TITLE":{"ko": "[ 빌드 envelope / 분말 ]","en": "[ Build envelope / Powder ]"},
    "RES_BUILD_H":  {"ko": "빌드 높이   : ",          "en": "Build height: "},
    "RES_BUILD_VOL":{"ko": "빌드 부피   : ",          "en": "Build volume: "},
    "RES_PACKING":  {"ko": "패킹률      : ",          "en": "Packing     : "},
    "RES_POWDER":   {"ko": "필요 분말  : ",           "en": "Powder reqd: "},

    # ── v2.992.beta-5: 상태 메시지 ──
    "MSG_OPEN_FIRST":{"ko": "STL을 먼저 열어주세요",
                       "en": "Please open an STL first"},
    "MSG_BBOX_NONE":{"ko": "BBox 정보 없음",          "en": "No bounding box info"},
    "MSG_NO_ANALYSIS":{"ko": "분석 결과 없음",        "en": "No analysis result"},
    "MSG_APPLY_DONE":{"ko": "✓ 변경사항 적용 완료 (3D + 결과 + 단면 갱신)",
                       "en": "✓ Changes applied (3D + Result + Slice updated)"},

    # ── v2.992.beta-5: 단면 단독창 Z 범위 dialog (v2.983 추가) ──
    "DLG_RENDER_RANGE":{"ko": "🎬 사전 렌더 — Z 범위 설정",
                         "en": "🎬 Pre-render — Z Range Setting"},
    "DLG_PART_RANGE":{"ko": "부품 Z 범위:",           "en": "Part Z range:"},
    "DLG_Z_START":  {"ko": "<b>시작 Z (mm):</b>",     "en": "<b>Start Z (mm):</b>"},
    "DLG_Z_END":    {"ko": "<b>끝 Z (mm):</b>",       "en": "<b>End Z (mm):</b>"},
    "DLG_Z_STEP":   {"ko": "<b>Step (mm):</b>",       "en": "<b>Step (mm):</b>"},
    "DLG_QUICK_PRESET":{"ko": "<b>빠른 설정:</b>",    "en": "<b>Quick preset:</b>"},
    "DLG_PRESET_ALL":{"ko": "전체",                   "en": "All"},
    "DLG_PRESET_LOWER":{"ko": "하단 1/2",             "en": "Lower 1/2"},
    "DLG_PRESET_UPPER":{"ko": "상단 1/2",             "en": "Upper 1/2"},
    "DLG_PRESET_CURR":{"ko": "현재 Z ±5mm",           "en": "Current Z ±5mm"},
    "DLG_RENDER_START":{"ko": "🎬 렌더 시작",         "en": "🎬 Start Render"},

    # ── v2.992.beta-5: 빌드/소재 탭 라벨 ──
    "LBL_EDM_MARGIN":{"ko": "EDM마진(mm):",            "en": "EDM margin (mm):"},
    "LBL_SAFETY":   {"ko": "안전마진:",                "en": "Safety:"},
    "LBL_PACKING_PCT":{"ko": "패킹률(%):",             "en": "Packing (%):"},
    "LBL_QTY":      {"ko": "수량:",                    "en": "Qty:"},
    "LBL_GAP":      {"ko": "Gap(mm):",                 "en": "Gap (mm):"},
    "LBL_PLATE":    {"ko": "Plate:",                   "en": "Plate:"},
    "LBL_FILE_NONE":{"ko": "(파일 없음)",              "en": "(no file)"},
    "LBL_SPEED":    {"ko": "속도:",                    "en": "Speed:"},
    "LBL_INTERVAL_MM":{"ko": "간격(mm):",              "en": "Interval (mm):"},
    "BTN_APPLY_CHANGES":{"ko": "✓ 변경사항 적용",      "en": "✓ Apply Changes"},
    "BTN_PACK_GRID":{"ko": "📦 격자 배치",             "en": "📦 Grid Layout"},
    "BTN_CLEAR_PREVIEW":{"ko": "✕ 미리보기 끄기",      "en": "✕ Clear Preview"},
    "BTN_RENDER":   {"ko": "🎬 렌더",                  "en": "🎬 Render"},
    "BTN_CLOSE":    {"ko": "닫기",                     "en": "Close"},
    "CHK_LOOP":     {"ko": "반복",                     "en": "Loop"},
    "GRP_VIEW":     {"ko": "◆ 시점",                   "en": "◆ View"},

    # ── v2.992.beta-5: 툴팁 ──
    "TT_LAYER_FIRST":{"ko": "처음 layer (z_min)",      "en": "First layer (z_min)"},
    "TT_LAYER_LAST":{"ko": "마지막 layer (z_max)",     "en": "Last layer (z_max)"},
    "TT_BOX_ZOOM":  {"ko": "Box zoom — 드래그로 영역 선택",
                       "en": "Box zoom — drag to select area"},

    # ── v2.992.beta-5: 상태 메시지 (lbl_status) ──
    "STA_OPEN_FIRST":{"ko": "STL을 먼저 열어주세요",   "en": "Please open an STL first"},
    "STA_WT_CHECKING":{"ko": "Watertight 검사 중...",  "en": "Checking watertight..."},
    "STA_NO_BASELINE":{"ko": "baseline 없음",          "en": "No baseline"},
    "STA_UNDO_CLEAR":{"ko": "실행 취소 기록 비움",     "en": "Undo history cleared"},
    "STA_STL_MISSING":{"ko": "STL/matplotlib 미설치",  "en": "STL / matplotlib not installed"},
    "STA_NO_PATH":  {"ko": "파일 경로 없음",           "en": "No file path"},
    "STA_3D_RESET": {"ko": "3D 시점 리셋 (Fit all)",   "en": "3D view reset (Fit all)"},
    "STA_DIR6_RUN": {"ko": "빌드 방향 6축 평가 중...", "en": "Evaluating build direction (6-axis)..."},
    "STA_DIR6_DONE":{"ko": "빌드 방향 비교 완료",      "en": "Build direction comparison done"},
    "STA_QTY_ZERO": {"ko": "수량이 0 — 배치 불필요",   "en": "Quantity is 0 — no layout"},
    "STA_NO_BBOX":  {"ko": "STL 미로드 — Bbox 없음",   "en": "STL not loaded — no bbox"},
    "STA_NO_MACHINE_LAYOUT":{"ko": "머신 미선택 — 격자 계산 불가",
                       "en": "No machine selected — layout unavailable"},
    "STA_NO_PLOTTER":{"ko": "3D plotter 없음",         "en": "No 3D plotter"},
    "STA_CANCEL_REQ":{"ko": "취소 요청됨...",          "en": "Cancel requested..."},
    "STA_CANCELED": {"ko": "취소됨",                   "en": "Canceled"},
    "STA_NO_OPEN_FILE":{"ko": "파일이 열려 있지 않음", "en": "No file open"},
    "STA_RELOAD_NONE":{"ko": "리로드 — 열려 있는 파일이 없음",
                       "en": "Reload — no file open"},
    "STA_RELOADING":{"ko": "리로드 중...",             "en": "Reloading..."},
    "STA_WT_FAIL":  {"ko": "Watertight 검사 실패",     "en": "Watertight check failed"},
    "STA_WALL_CANCEL_REQ":{"ko": "Wall 분석 취소 요청...",
                       "en": "Wall analysis cancel requested..."},
    "STA_WALL_CANCEL_DONE":{"ko": "Wall thickness 분석 취소 완료",
                       "en": "Wall thickness analysis canceled"},
    "STA_WALL_FAIL":{"ko": "Wall 계산 실패",           "en": "Wall calculation failed"},
    "STA_FIX_DONE": {"ko": "Fixing 적용 완료",         "en": "Fixing applied"},
    "STA_NO_HOLES": {"ko": "Hole 없음",                "en": "No holes"},
    "STA_NO_ANALYSIS":{"ko": "분석 결과 없음 — STL 을 먼저 분석하세요",
                       "en": "No analysis — please analyze STL first"},
    "STA_RENDERING":{"ko": "⚙  렌더링 중...",           "en": "⚙  Rendering..."},
    "STA_CLIP_OFF": {"ko": "[3D 단독] 모든 Clipping Off",
                       "en": "[3D Standalone] All Clipping Off"},
    "STA_NO_UNDO":  {"ko": "실행 취소할 작업이 없습니다",
                       "en": "Nothing to undo"},
    "STA_NO_REDO":  {"ko": "다시 실행할 작업이 없습니다",
                       "en": "Nothing to redo"},
    "STA_NO_MACHINE":{"ko": "머신 미선택",             "en": "No machine selected"},
    "STA_MACHINE_APPLIED":{"ko": "장비 적용: {name}",  "en": "Machine applied: {name}"},
    # v2.992.beta-5 hotfix16: GPU_DLG_* 키 11개 제거 — CuPy 폐기로 toggle dialog 삭제됨.
    # 신규 BACKEND_DLG_* 키가 대체 (Numba 정보 표시).
    "BTN_CLOSE":             {"ko": "닫기",                       "en": "Close"},
    "STA_ANIM_STOP":{"ko": "단면 애니메이션 정지",     "en": "Slice animation stopped"},
    "STA_ROT_RESET":{"ko": "회전 리셋",                "en": "Rotation reset"},
    "STA_APPLY_DONE":{"ko": "✓ 변경사항 적용 완료 (3D + 결과 + 단면 갱신)",
                       "en": "✓ Changes applied (3D + Result + Slice updated)"},

    # ── v2.992.beta-5: QMessageBox 타이틀 ──
    "TIT_WALL_FAIL":{"ko": "Wall 분석 실패",           "en": "Wall analysis failed"},
    "TIT_WALL_RESULT":{"ko": "Wall 분석 결과",         "en": "Wall analysis result"},
    "TIT_GRID":     {"ko": "격자 배치",                "en": "Grid Layout"},
    "TIT_LOAD_FAIL":{"ko": "로드 실패",                "en": "Load failed"},
    "TIT_HOLE":     {"ko": "Hole 검사",                "en": "Hole check"},
    "TIT_FIX":      {"ko": "Fixing",                   "en": "Fixing"},
    "TIT_ANALYSIS_FAIL":{"ko": "분석 실패",            "en": "Analysis failed"},
    "TIT_WARN":     {"ko": "경고",                     "en": "Warning"},
    "TIT_ERROR":    {"ko": "오류",                     "en": "Error"},
    "TIT_NOTICE":   {"ko": "알림",                     "en": "Notice"},
    "TIT_CONFIRM":  {"ko": "확인",                     "en": "Confirm"},
    "TIT_INFO":     {"ko": "정보",                     "en": "Info"},
    "TIT_SAVE_FAIL":{"ko": "저장 실패",                "en": "Save failed"},
    "TIT_EXPORT":   {"ko": "내보내기",                 "en": "Export"},
    "TIT_OPEN_FAIL":{"ko": "열기 실패",                "en": "Open failed"},

    # ── v2.992.beta-5: 파일 필터 ──
    "FILTER_STL":   {"ko": "STL 파일 (*.stl)",         "en": "STL files (*.stl)"},
    "FILTER_TXT":   {"ko": "텍스트 파일 (*.txt)",      "en": "Text files (*.txt)"},
    "FILTER_PNG":   {"ko": "PNG 이미지 (*.png)",       "en": "PNG image (*.png)"},

    # ── v2.992.beta-5: 회전/스케일 탭 ──
    "LBL_PCA":      {"ko": "PCA 자동:",                "en": "PCA auto:"},
    "LBL_SCALE":    {"ko": "스케일:",                  "en": "Scale:"},
    "LBL_UNIT":     {"ko": "단위:",                    "en": "Unit:"},
    "LBL_ROT_X":    {"ko": "X (deg):",                 "en": "X (deg):"},
    "LBL_ROT_Y":    {"ko": "Y (deg):",                 "en": "Y (deg):"},
    "LBL_ROT_Z":    {"ko": "Z (deg):",                 "en": "Z (deg):"},

    # ── v2.992.beta-5: 단축키 도움말 dialog ──
    "SC_DIALOG_TITLE":{"ko": "단축키 — STL Analyzer",  "en": "Shortcuts — STL Analyzer"},
    "SC_HEADER":    {"ko": "<b>단축키 일람</b>",       "en": "<b>Shortcut List</b>"},
    "SC_COL_KEY":   {"ko": "단축키",                   "en": "Key"},
    "SC_COL_DESC":  {"ko": "기능",                     "en": "Function"},
    "SC_COL_SRC":   {"ko": "소속",                     "en": "Source"},
    "SC_SRC_MENU":  {"ko": "메뉴",                     "en": "Menu"},
    "SC_SRC_AUX":   {"ko": "보조",                     "en": "Aux"},
    "SC_NOTE":      {"ko": "<i>3D 단독창 내 추가 단축키: X / Y / Z (축 모드 순환), "
                              "Shift+X/Y/Z (축 리셋), Esc (전체 리셋)</i>",
                     "en": "<i>Additional shortcuts in 3D standalone: X / Y / Z (axis mode cycle), "
                              "Shift+X/Y/Z (axis reset), Esc (reset all)</i>"},

    # 단축키 기능 설명 — 메뉴
    "SC_OPEN":      {"ko": "STL 파일 열기",            "en": "Open STL file"},
    "SC_SAVE":      {"ko": "현재 STL 저장",            "en": "Save current STL"},
    "SC_SAVE_SUPP": {"ko": "Support STL 저장",         "en": "Save Support STL"},
    "SC_SAVE_REP":  {"ko": "분석 보고서 저장 (.txt)",  "en": "Save analysis report (.txt)"},
    "SC_CLOSE":     {"ko": "창 닫기 / 종료",           "en": "Close window / Exit"},
    "SC_REANALYZE": {"ko": "재분석",                   "en": "Re-analyze"},
    "SC_FIX":       {"ko": "고급 Fixing",              "en": "Advanced Fixing"},
    "SC_HELP":      {"ko": "단축키 도움말",            "en": "Shortcut help"},

    # 단축키 기능 설명 — 보조
    "SC_REANALYZE_ALIAS":{"ko": "재분석 (=F5)",        "en": "Re-analyze (=F5)"},
    "SC_WALL":      {"ko": "Wall thickness 분석",      "en": "Wall thickness analysis"},
    "SC_HOLE":      {"ko": "Hole 자동 채우기",         "en": "Auto-fill holes"},
    "SC_BUILD_OPT": {"ko": "빌드 방향 최적화",         "en": "Build direction optimization"},
    "SC_PACK":      {"ko": "다중 부품 자동 Packing",   "en": "Auto-pack multiple parts"},
    "SC_CANCEL":    {"ko": "취소 (실행 중 작업)",      "en": "Cancel (running task)"},
    "SC_MODE_EDGE": {"ko": "렌더 모드: Edge Only",     "en": "Render mode: Edge Only"},
    "SC_MODE_SOFT": {"ko": "렌더 모드: Soft (음영)",   "en": "Render mode: Soft (shaded)"},
    "SC_MODE_SOLID":{"ko": "렌더 모드: Solid",         "en": "Render mode: Solid"},
    "SC_MODE_SUPP": {"ko": "렌더 모드: Support",       "en": "Render mode: Support"},
    "SC_MODE_FEAT": {"ko": "렌더 모드: Feature Edge",  "en": "Render mode: Feature Edge"},
    "SC_FULLSCREEN":{"ko": "전체화면 토글 (단독창)",   "en": "Toggle fullscreen (standalone)"},
    "SC_MDS":       {"ko": "MDS (재료 데이터 시트) 보기","en": "Show MDS (Material Data Sheet)"},

    # ── v2.992.beta-5: 잔여 라벨/버튼/툴팁 일괄 ──
    # 툴팁 (slice / 단독창)
    "TT_LAYER_Z_MIN":{"ko": "처음 layer (z_min)",      "en": "First layer (z_min)"},
    "TT_LAYER_Z_MAX":{"ko": "마지막 layer (z_max)",    "en": "Last layer (z_max)"},
    "TT_BOX_ZOOM_DRAG":{"ko": "Box zoom — 드래그로 영역 선택",
                       "en": "Box zoom — drag to select area"},
    "TT_RELOAD_FILE":{"ko": "리로드 — 현재 파일 다시 읽기",
                       "en": "Reload — re-read current file"},
    "TT_REANALYZE_F5":{"ko": "재분석 (F5)",            "en": "Re-analyze (F5)"},
    "TT_DIAG_FIX":  {"ko": "진단 + 항목별 Fix + 통합 Fixing",
                       "en": "Diagnose + per-item fix + unified Fixing"},
    "TT_CANCEL":    {"ko": "취소",                     "en": "Cancel"},
    "TT_FLIP":      {"ko": "빌드 방향 반전 (180° 회전)",
                       "en": "Flip build direction (180° rotate)"},
    "TT_SAFETY":    {"ko": "1.0=원본, 1.2=+20%",       "en": "1.0=original, 1.2=+20%"},
    "TT_GAP":       {"ko": "격자 배치 시 부품 간격",   "en": "Part spacing for grid layout"},
    "TT_PACK":      {"ko": "플레이트 위에 수량만큼 격자 배치 미리보기",
                       "en": "Grid-layout preview on plate (by qty)"},
    "TT_CLEAR_PREV":{"ko": "3D 뷰에서 격자 배치 미리보기 박스 모두 제거",
                       "en": "Remove all grid-layout boxes from 3D view"},
    "TT_ROT_RESET": {"ko": "회전 리셋",                "en": "Rotation reset"},
    "TT_RELOAD_ORIG":{"ko": "원본 재로드",             "en": "Reload original"},
    "TT_PCA":       {"ko": "주성분 분석 — 가장 긴 축을 Z로 정렬",
                       "en": "PCA — align longest axis to Z"},
    "TT_Z_DOWN":    {"ko": "Z 위치 ↓ (Step 만큼)",     "en": "Z position ↓ (by Step)"},
    "TT_Z_UP":      {"ko": "Z 위치 ↑ (Step 만큼)",     "en": "Z position ↑ (by Step)"},
    "TT_PLAY_PAUSE":{"ko": "재생 / 일시정지",          "en": "Play / Pause"},
    "TT_PLAY_PAUSE_ZOOM":{"ko": "재생 / 일시정지 (zoom 유지)",
                       "en": "Play / Pause (keep zoom)"},
    "TT_CACHE_STAT":{"ko": "렌더 캐시 상태",           "en": "Render cache state"},
    "TT_RULER_CLEAR":{"ko": "Ruler 삭제 — 그어진 모든 ruler 제거 ",
                       "en": "Clear rulers — remove all drawn rulers"},
    "TT_RULER_CLEAR2":{"ko": "Ruler 삭제 — 우클릭 2회 = 새 ruler",
                       "en": "Clear ruler — right-click 2x = new ruler"},
    "TT_ARC_R":     {"ko": "ON 시 좌클릭 3점 → 원호 R / Center 표시. 우클릭 = 모드 해제 (라벨 유지)",
                       "en": "When ON, left-click 3 points → arc R / center. Right-click = release (keep labels)"},
    "TT_FILE_CURRENT":{"ko": "현재 STL 파일",          "en": "Current STL file"},
    "TT_TRI_COUNT": {"ko": "삼각형 개수",              "en": "Triangle count"},
    "TT_BUILD_DIR_CURRENT":{"ko": "현재 빌드 방향",    "en": "Current build direction"},
    "TT_PLATE_SIZE":{"ko": "현재 선택 장비 + plate 크기",
                       "en": "Current machine + plate size"},
    "TT_Z_STEP":    {"ko": "▼/▲ 클릭 시 이동 거리 (mm)",
                       "en": "▼/▲ click step (mm)"},
    "TT_LAYER_GAP": {"ko": "layer 간격 — 작을수록 부드러우나 메모리 ↑",
                       "en": "Layer gap — smaller = smoother, more memory"},
    "TT_PART_FULL": {"ko": "부품 전체 Z 범위",         "en": "Part full Z range"},
    "TT_PART_LOWER":{"ko": "부품 하단 절반 (z_min ~ 중간)",
                       "en": "Part lower half (z_min ~ middle)"},
    "TT_PART_UPPER":{"ko": "부품 상단 절반 (중간 ~ z_max)",
                       "en": "Part upper half (middle ~ z_max)"},
    "TT_Z_RANGE_5MM":{"ko": "현재 Z 위치 ±5mm 범위",   "en": "Current Z position ±5mm range"},

    # 라벨 — 단독창 / 빌드 / 회전
    "LBL_IDLE":     {"ko": "대기 중",                  "en": "Idle"},
    # v2.992.beta-5: progress bar generic 키 — 영어 모드 시 한글 leak 방지
    "PB_DONE":      {"ko": "완료",                     "en": "Done"},
    "PB_FAIL":      {"ko": "실패",                     "en": "Failed"},
    "PB_LOADING":   {"ko": "불러오는 중",              "en": "Loading"},
    "PB_ANALYZING": {"ko": "분석 중",                  "en": "Analyzing"},
    "PB_SLICING":   {"ko": "슬라이싱 중",              "en": "Slicing"},
    "PB_FIXING":    {"ko": "수정 중",                  "en": "Fixing"},
    "PB_SAVING":    {"ko": "저장 중",                  "en": "Saving"},
    "PB_SAVE_STL":  {"ko": "STL 저장 ({n} tri)",       "en": "Save STL ({n} tri)"},
    "PB_SAVE_SUPP": {"ko": "Support STL 저장 ({n} tri)",
                                                       "en": "Save Support STL ({n} tri)"},
    "PB_CANCELING": {"ko": "취소 중...",               "en": "Canceling..."},
    "PB_WORKER_START":{"ko": "워커 시작...",           "en": "Worker starting..."},
    "PB_PROGRESS":  {"ko": "진행: {msg}",              "en": "Progress: {msg}"},
    "PB_TRI_COUNT": {"ko": "{n} 삼각형",               "en": "{n} triangles"},
    "PB_WALL_PCT":  {"ko": "Wall {p}%",                "en": "Wall {p}%"},
    "PB_WALL_CANCELING":{"ko": "Wall 취소 중...",      "en": "Wall canceling..."},
    "PB_WALL_CANCEL_DONE":{"ko": "Wall 취소 완료",     "en": "Wall canceled"},
    "PB_WALL_DONE": {"ko": "Wall 완료",                "en": "Wall done"},
    "PB_WALL_FAIL": {"ko": "Wall 실패",                "en": "Wall failed"},
    "MSG_WALL_CANCELED":{"ko": "Wall thickness 분석이 취소되었습니다.\n부분 결과는 적용하지 않습니다.",
                         "en": "Wall thickness analysis canceled.\nPartial results not applied."},
    "STA_LOAD_DONE":{"ko": "로드 완료: {name}",         "en": "Load done: {name}"},
    "BTN_CANCEL_ICO":{"ko": "✕ 취소",                  "en": "✕ Cancel"},
    "LBL_MATERIAL2":{"ko": "재료:",                    "en": "Material:"},
    "LBL_DENSITY":  {"ko": "밀도(g/cm³):",             "en": "Density (g/cm³):"},
    "LBL_MACHINE":  {"ko": "장비:",                    "en": "Machine:"},
    "LBL_BUILD":    {"ko": "빌드:",                    "en": "Build:"},
    "LBL_ROT_DEG":  {"ko": "<b>회전(°):</b>",          "en": "<b>Rotate (°):</b>"},
    "LBL_SCALE_B":  {"ko": "<b>스케일:</b>",           "en": "<b>Scale:</b>"},
    "LBL_RATIO":    {"ko": "배율:",                    "en": "Ratio:"},
    "LBL_DISPLAY_RANGE":{"ko": "표시 범위:",           "en": "Display range:"},
    "LBL_DISPLAY_RANGE_DEG":{"ko": "표시 범위 (°):",   "en": "Display range (°):"},
    "LBL_Z_POS":    {"ko": "◆ Z 위치 (mm)",            "en": "◆ Z position (mm)"},
    "LBL_CENTER_COORD":{"ko": "<b>중심 좌표:</b>",     "en": "<b>Center coord:</b>"},
    "LBL_BN":       {"ko": "BN (Border 갯수):",        "en": "BN (Border count):"},
    "LBL_BC":       {"ko": "BC (경계 offset):",        "en": "BC (boundary offset):"},
    "LBL_BD":       {"ko": "BD (Border 간격):",        "en": "BD (Border gap):"},
    "LBL_HO":       {"ko": "HO (Hatch 시작):",         "en": "HO (Hatch start):"},
    "LBL_HD":       {"ko": "HD (Hatch 간격):",         "en": "HD (Hatch gap):"},
    "LBL_HA":       {"ko": "HA (각도):",               "en": "HA (angle):"},
    "LBL_HA_INC":   {"ko": "HA 증분 (°/layer):",       "en": "HA increment (°/layer):"},
    "LBL_AREA_NONE":{"ko": "단면적: -- mm²",           "en": "Section area: -- mm²"},
    "LBL_FILE_NONE_ICON":{"ko": "📁 (없음)",           "en": "📁 (none)"},
    "LBL_EDGE_WIDTH":{"ko": "교선 두께:",              "en": "Edge width:"},
    "LBL_Z_START":  {"ko": "<b>시작 Z (mm):</b>",      "en": "<b>Start Z (mm):</b>"},
    "LBL_Z_END":    {"ko": "<b>끝 Z (mm):</b>",        "en": "<b>End Z (mm):</b>"},
    "LBL_QUICK_PRESET":{"ko": "<b>빠른 설정:</b>",     "en": "<b>Quick preset:</b>"},

    # 버튼
    "BTN_OPEN":     {"ko": "📂 파일 열기 (Ctrl+O)",    "en": "📂 Open file (Ctrl+O)"},
    "BTN_FIXING":   {"ko": "🔧 고급 Fixing (F7)",      "en": "🔧 Advanced Fixing (F7)"},
    "BTN_CLEAR_CONSOLE":{"ko": "✕ 콘솔 지우기",        "en": "✕ Clear console"},
    "BTN_MDS":      {"ko": "MDS 보기",                 "en": "Show MDS"},
    "BTN_APPLY_ROT":{"ko": "▶ 회전 적용",              "en": "▶ Apply rotation"},
    "BTN_APPLY_SCALE":{"ko": "✓ 스케일 적용",          "en": "✓ Apply scale"},
    "BTN_ORIG":     {"ko": "↻ 원본",                   "en": "↻ Original"},
    "BTN_APPLY_RANGE":{"ko": "범위 적용",              "en": "Apply range"},
    "BTN_PCA":      {"ko": "🎯 PCA 자동 정렬",          "en": "🎯 PCA auto-align"},
    "BTN_3D_STANDALONE":{"ko": "🪟 3D 단독창 (디테일 뷰)",
                       "en": "🪟 3D standalone (detail view)"},
    "BTN_DOWN":     {"ko": "▼ 아래",                   "en": "▼ Down"},
    "BTN_UP":       {"ko": "▲ 위",                     "en": "▲ Up"},
    "BTN_SLICE_STANDALONE":{"ko": "🪟 단면 단독창",    "en": "🪟 Slice standalone"},
    "BTN_CENTER":   {"ko": "⌂ 중앙",                   "en": "⌂ Center"},
    "BTN_CENTER_ALL":{"ko": "⌂ 모두 중앙",             "en": "⌂ Center all"},
    "BTN_ARC_R":    {"ko": "⌒ 원호R 측정",              "en": "⌒ Arc R measure"},
    "BTN_APPLY":    {"ko": "✓ 적용",                   "en": "✓ Apply"},
    "BTN_APPLY_PLAIN":{"ko": "적용",                   "en": "Apply"},
    "BTN_MULTIVIEW":{"ko": "📐 4-Pane 멀티뷰 열기",     "en": "📐 Open 4-Pane multiview"},
    "BTN_ALL_OFF":  {"ko": "✕ 모두 Off",                "en": "✕ All Off"},
    "BTN_ALL":      {"ko": "전체",                     "en": "All"},
    "BTN_LOWER_HALF":{"ko": "하단 1/2",                "en": "Lower 1/2"},
    "BTN_UPPER_HALF":{"ko": "상단 1/2",                "en": "Upper 1/2"},
    "BTN_REANALYZE":{"ko": "재분석",                   "en": "Re-analyze"},

    # ── v2.992.beta-5 hotfix: 잔여 msgbox 타이틀 37건 ──
    "TIT_MULTIVIEW_FAIL": {"ko": "Multi-view 단면 실패",     "en": "Multi-view slice failed"},
    "TIT_SLICE_DLG_FAIL": {"ko": "단면 단독창 실패",         "en": "Slice standalone failed"},
    "TIT_QT_ANALYSIS_FAIL":{"ko": "Qt 분석 다이얼로그 실패",  "en": "Qt analysis dialog failed"},
    "TIT_ANALYTICS_FAIL": {"ko": "Analytics 실패",           "en": "Analytics failed"},
    "TIT_BUILD_CMP":      {"ko": "빌드 방향 비교",           "en": "Build direction comparison"},
    "TIT_BUILD_CMP_FAIL": {"ko": "빌드 방향 비교 실패",      "en": "Build direction comparison failed"},
    "TIT_GRID_FAIL":      {"ko": "격자 배치 실패",           "en": "Grid layout failed"},
    "TIT_CORE_LOAD_FAIL": {"ko": "core 로드 실패",           "en": "core load failed"},
    "TIT_RELOAD":         {"ko": "리로드",                   "en": "Reload"},
    "TIT_RELOAD_FAIL":    {"ko": "리로드 실패",              "en": "Reload failed"},
    "TIT_WATERTIGHT_FAIL":{"ko": "Watertight 실패",          "en": "Watertight failed"},
    "TIT_WALL_REMOVED":   {"ko": "벽 두께 분석 — 제거됨",    "en": "Wall thickness — removed"},
    "TIT_WALL_CANCEL":    {"ko": "Wall 분석 취소",           "en": "Wall analysis canceled"},
    "TIT_FIX_DLG_FAIL":   {"ko": "Fixing 다이얼로그 실패",   "en": "Fixing dialog failed"},
    "TIT_FIX_ERROR":      {"ko": "Fixing 에러",              "en": "Fixing error"},
    "TIT_HOLE_FAIL":      {"ko": "Hole 검사 실패",           "en": "Hole check failed"},
    "TIT_STL_SAVE":       {"ko": "STL 저장",                 "en": "Save STL"},
    "TIT_STL_SAVE_DONE":  {"ko": "STL 저장 완료",            "en": "STL saved"},
    "TIT_STL_SAVE_FAIL":  {"ko": "STL 저장 실패",            "en": "STL save failed"},
    "TIT_REPORT_SAVE":    {"ko": "보고서 저장",              "en": "Save report"},
    "TIT_REPORT_SAVE_DONE":{"ko": "보고서 저장 완료",        "en": "Report saved"},
    "TIT_REPORT_SAVE_FAIL":{"ko": "보고서 저장 실패",        "en": "Report save failed"},
    "TIT_SAVE_DONE":      {"ko": "저장 완료",                "en": "Save complete"},
    "TIT_SUPPORT_FAIL":   {"ko": "Support 실패",             "en": "Support failed"},
    "TIT_MDS_CALL_ERR":   {"ko": "MDS 호출 에러",            "en": "MDS call error"},
    "TIT_MDS_DLG_FAIL":   {"ko": "MDS 다이얼로그 실패",      "en": "MDS dialog failed"},
    "TIT_MDS_ERR":        {"ko": "MDS 에러",                 "en": "MDS error"},
    "TIT_HELP_FAIL":      {"ko": "Help 실패",                "en": "Help failed"},
    "TIT_3D_DLG_FAIL":    {"ko": "3D 단독창 실패",           "en": "3D standalone failed"},
    "TIT_GPU_WIN_FAIL":   {"ko": "GPU 창 실패",              "en": "GPU window failed"},
    "TIT_PCA_FAIL":       {"ko": "PCA 정렬 실패",            "en": "PCA align failed"},
    "TIT_ROT_FAIL":       {"ko": "회전 실패",                "en": "Rotation failed"},
    "TIT_SCALE_FAIL":     {"ko": "스케일 실패",              "en": "Scale failed"},
    "TIT_PRERENDER":      {"ko": "사전 렌더",                "en": "Pre-render"},
    "TIT_SCREENSHOT_DONE":{"ko": "스크린샷 완료",            "en": "Screenshot saved"},
    "TIT_SCREENSHOT_FAIL":{"ko": "스크린샷 실패",            "en": "Screenshot failed"},
    "TIT_EXIT_CONFIRM":   {"ko": "종료 확인",                "en": "Exit confirmation"},

    # ── v2.992.beta-5: 외부 dialog 번역 키 ──
    # fixing_dialog (FX_*)
    "FX_TITLE":            {"ko": "고급 Fixing (v2.916 hotfix2)", "en": "Advanced Fixing"},
    "FX_DIAG_HEADER":      {"ko": "<b>◆ 진단 결과 + 항목별 Fix</b>", "en": "<b>◆ Diagnosis + Per-item Fix</b>"},
    "FX_LOG_HEADER":       {"ko": "<b>◆ 실행 로그</b>",        "en": "<b>◆ Execution Log</b>"},
    "FX_CTRL_HEADER":      {"ko": "◆ Fixing 컨트롤",            "en": "◆ Fixing Controls"},
    "FX_BTN_DIAG":         {"ko": "🔍 진단",                    "en": "🔍 Diagnose"},
    "FX_BTN_ALL":          {"ko": "⚡ 통합 Fixing",              "en": "⚡ Unified Fixing"},
    "FX_BTN_APPLY":        {"ko": "✓ 적용",                     "en": "✓ Apply"},
    "FX_STA_IDLE":         {"ko": "대기 중",                    "en": "Idle"},
    "FX_STA_DIAG":         {"ko": "진단 중...",                 "en": "Diagnosing..."},
    "FX_STA_DIAG_DONE":    {"ko": "진단 완료",                  "en": "Diagnosis complete"},
    "FX_STA_FIX_DONE":     {"ko": "완료",                       "en": "Complete"},
    "FX_STA_FAIL":         {"ko": "실패",                       "en": "Failed"},
    "FX_TABLE_COL":        {"ko": "항목,값,상태,동작",          "en": "Item,Value,Status,Action"},
    "FX_NO_RESULT_TITLE":  {"ko": "결과 없음",                  "en": "No result"},
    "FX_NO_RESULT_MSG":    {"ko": "먼저 Fixing 실행하세요.",    "en": "Run Fixing first."},
    "FX_APPLY_TITLE":      {"ko": "Fixing 적용",                "en": "Fixing applied"},
    "FX_APPLY_FAIL":       {"ko": "적용 실패",                  "en": "Apply failed"},

    # mds_dialog (MD_*)
    "MD_CMP_ITEM":         {"ko": "<b>비교 항목</b>",           "en": "<b>Comparison Item</b>"},
    "MD_MAT":              {"ko": "<b>재료:</b>",               "en": "<b>Material:</b>"},
    "MD_BASIC_PHYS":       {"ko": "기본 물리 / 열적 (열처리 무관)", "en": "Basic Physical / Thermal (heat-treat agnostic)"},
    "MD_HEAT_TREAT":       {"ko": "◆ 열처리 별 기계적 물성 + 표면조도", "en": "◆ Mechanical Properties + Surface Roughness by Heat Treatment"},
    "MD_NO_HEAT":          {"ko": "(열처리 데이터 없음)",       "en": "(No heat-treatment data)"},
    "MD_VENDORS_OFFICIAL": {"ko": "공식 지원 회사 (체크리스트)", "en": "Official Vendors (checklist)"},
    "MD_VENDORS_EXTRA":    {"ko": "<b>추가 지원사:</b>",        "en": "<b>Additional vendors:</b>"},
    "MD_COMP":             {"ko": "화학 조성 (% by weight)",    "en": "Chemical Composition (% by weight)"},
    "MD_REF":              {"ko": "참고 자료 (TDS / 논문)",     "en": "References (TDS / papers)"},
    "MD_NO_DATA":          {"ko": "데이터 없음",                "en": "No data"},
    "MD_PROP_HEADER":      {"ko": "<b>물성 데이터</b>",         "en": "<b>Properties</b>"},
    "MD_DENSITY":          {"ko": "밀도",                       "en": "Density"},
    "MD_E":                {"ko": "탄성률 E",                   "en": "Young's modulus E"},
    "MD_MELT":             {"ko": "녹는점",                     "en": "Melting point"},
    "MD_CTE":              {"ko": "열팽창",                     "en": "CTE"},
    "MD_HARD":             {"ko": "경도",                       "en": "Hardness"},
    "MD_TENSILE":          {"ko": "인장",                       "en": "Tensile"},
    "MD_VENDOR_VIEW":      {"ko": "벤더 보기",                  "en": "View vendor"},

    # analytics_dialog (AN_*)
    "AN_HEADER":           {"ko": "◆ 메시 분석 결과",           "en": "◆ Mesh Analysis Result"},
    "AN_WT_OK":            {"ko": "✅ Watertight (열린 엣지 없음)", "en": "✅ Watertight (no open edges)"},
    "AN_AUTO_FIX":         {"ko": "✓ 자동 보정:",               "en": "✓ Auto-fix:"},
    "AN_TAB_GEO":          {"ko": "📐 기하",                    "en": "📐 Geometry"},
    "AN_TAB_INT":          {"ko": "🔧 무결성",                  "en": "🔧 Integrity"},
    "AN_TAB_TIME":         {"ko": "⏱ 빌드 시간",                "en": "⏱ Build Time"},

    # pyvista_window (PW_*)
    "PW_VIEW":             {"ko": "시점",                       "en": "View"},
    "PW_VIS":              {"ko": "가시성",                     "en": "Visibility"},
    "PW_COLOR_MODE":       {"ko": "색상 모드",                  "en": "Color Mode"},
    "PW_SUPPORT_DEG":      {"ko": "Support 임계각 (°)",         "en": "Support threshold (°)"},

    # v2.992.beta-5 추가: fixing_dialog 동적 상태 메시지
    "FX_STA_DIAG_FAIL":    {"ko": "진단 실패: ",                "en": "Diagnose failed: "},
    "FX_STA_EXEC_FAIL":    {"ko": "실행 실패: ",                "en": "Execute failed: "},
    "FX_STA_UNI_RUN":      {"ko": "통합 Fixing...",             "en": "Unified Fixing..."},
    "FX_STA_UNI_DONE":     {"ko": "통합 완료",                  "en": "Unified done"},
    "FX_STA_UNI_FAIL":     {"ko": "통합 실패: ",                "en": "Unified failed: "},

    # ── v2.992.beta-5 hotfix: main_window.py 잔여 라벨 ──
    # QGroupBox 제목 (panel headers)
    "GRP_3D_PREVIEW":  {"ko": "3D 미리보기",         "en": "3D Preview"},
    "GRP_RENDER_MODE": {"ko": "렌더 모드",           "en": "Render Mode"},
    "GRP_RENDER_MODE_D":{"ko": "◆ 렌더 모드",        "en": "◆ Render Mode"},
    "GRP_SLICE_VIEW":  {"ko": "단면 보기 (Cross-Section)", "en": "Slice View (Cross-Section)"},
    "GRP_Z_ANIM":      {"ko": "🎞 Z 애니메이션",      "en": "🎞 Z Animation"},
    "GRP_HATCH":       {"ko": "해칭",                "en": "Hatching"},
    "GRP_SUPPORT_DEG": {"ko": "◆ 서포트 영역 (각도)","en": "◆ Support Range (angle)"},
    "GRP_SLICE_RENDER":{"ko": "🎬 단면 렌더 (Slice Render)", "en": "🎬 Slice Render"},

    # QCheckBox 옵션
    "CHK_AUTOFIX":     {"ko": "자동Fixing",          "en": "AutoFix"},
    "CHK_3D_PREVIEW":  {"ko": "3D 미리보기",         "en": "3D Preview"},
    "CHK_MP_POST":     {"ko": "MP 후처리",            "en": "MP post-process"},
    "CHK_VERBOSE_LOG": {"ko": "상세 로그",           "en": "Verbose log"},
    "CHK_HATCH":       {"ko": "해칭",                "en": "Hatching"},
    "CHK_SHOW":        {"ko": "표시",                "en": "Show"},
    "CHK_SLICER_PREV": {"ko": "Slicer 미리보기 표시","en": "Show slicer preview"},

    # QLabel — slice render 패널
    "LBL_AXIS_B":      {"ko": "<b>축:</b>",          "en": "<b>Axis:</b>"},
    "LBL_DIR_B":       {"ko": "<b>방향:</b>",        "en": "<b>Direction:</b>"},
    "LBL_START":       {"ko": "시작:",               "en": "Start:"},
    "LBL_END":         {"ko": "끝:",                 "en": "End:"},
    "LBL_SPEED_C":     {"ko": "속도:",               "en": "Speed:"},
    "LBL_CACHE_NONE":  {"ko": "캐시: 없음",          "en": "Cache: none"},
    "LBL_IDLE_STOPPED":{"ko": "정지 중",             "en": "Stopped"},

    # QPushButton — 잔여
    "BTN_UNFREEZE":    {"ko": "❄ 복귀",              "en": "❄ Unfreeze"},
    "BTN_PRERENDER":   {"ko": "🎞 사전 렌더",         "en": "🎞 Pre-render"},
    "BTN_PRESET_CURR": {"ko": "현재 Z ±5mm",         "en": "Current Z ±5mm"},

    # setWindowTitle
    "WIN_SLICE_DLG":   {"ko": "단면 보기 — 단독창 (고급)", "en": "Slice View — Standalone (advanced)"},
    "WIN_BUILD_CMP":   {"ko": "빌드 방향 6축 score 비교", "en": "Build Direction — 6-axis Score Comparison"},
    "WIN_PRERENDER":   {"ko": "🎬 사전 렌더 — Z 범위 설정", "en": "🎬 Pre-render — Z Range Setting"},
    "WIN_PRERENDER_S": {"ko": "Pre-render (단면 캐시)", "en": "Pre-render (Slice cache)"},

    # setText 동적/정적 라벨
    "STA_AREA":        {"ko": "단면적: ",            "en": "Section area: "},
    "STA_ARC_LINEAR":  {"ko": "원호R: 3점이 일직선", "en": "Arc R: 3 points are collinear"},
    "STA_ARC_R":       {"ko": "원호 R = ",           "en": "Arc R = "},
    "STA_DIST":        {"ko": "거리 ",               "en": "Distance "},
    "STA_RELOADING2":  {"ko": "리로드 중...",        "en": "Reloading..."},
    "STA_WT_CHECK2":   {"ko": "Watertight 검사 중...","en": "Checking watertight..."},
    "STA_SUPP_TRI_NO": {"ko": "Support: triangle 형식 미지원", "en": "Support: triangle format not supported"},
    "STA_CACHE_NONE":  {"ko": "캐시: 없음",          "en": "Cache: none"},
    "STA_INVALID_RANGE":{"ko": "⚠ 잘못된 범위/Step", "en": "⚠ Invalid range/step"},
    "STA_DONE_CACHE":  {"ko": "✓ 완료 (캐시)",       "en": "✓ Done (cache)"},
    "STA_DONE_REAL":   {"ko": "✓ 완료 (실시간)",     "en": "✓ Done (realtime)"},
    "STA_INITIAL_POS": {"ko": "⏮ 초기 위치",         "en": "⏮ Initial position"},
    "STA_CACHE_CLEAR": {"ko": "🗑 캐시 비움",         "en": "🗑 Cache cleared"},
    "STA_RENDERING2":  {"ko": "⚙  렌더링 중...",      "en": "⚙  Rendering..."},
    "STA_ORTHO":       {"ko": "직교",                "en": "Ortho"},
    "STA_SUPP_RANGE_BAD":{"ko": "Support 범위: lo < hi 이어야 함", "en": "Support range: lo < hi required"},
    "STA_SUPP_COLOR_RESET":{"ko": "Support 컬러 리셋 (기본 5색)", "en": "Support color reset (default 5)"},
    "STA_TRI_FORMAT_FAIL":{"ko": "triangles 형식 인식 실패", "en": "triangles format unrecognized"},
    "STA_NEED_ANALYZE":{"ko": "STL 을 먼저 분석하세요","en": "Please analyze STL first"},
    "STA_NO_BBOX2":    {"ko": "BBox 정보 없음",      "en": "No bbox info"},
    "STA_RENDER_START":{"ko": "🎬 렌더 시작",         "en": "🎬 Start render"},
    "STA_CANCEL2":     {"ko": "취소",                "en": "Cancel"},
    "STA_INVALID_Z":   {"ko": "⚠ 잘못된 Z 범위 / Step", "en": "⚠ Invalid Z range/step"},
    "STA_SLICER_FAIL": {"ko": "Slicer 로드 실패",    "en": "Slicer load failed"},
    "STA_VERTS_FAIL":  {"ko": "verts 추출 실패",     "en": "verts extraction failed"},
    "STA_NO_3D":       {"ko": "3D 뷰 없음 (PyVista 로드 실패)", "en": "No 3D view (PyVista load failed)"},

    # setToolTip 잔여
    "TT_RULER_CLEAR_ALL":{"ko": "Ruler 삭제 — 그어진 모든 ruler 제거 ", "en": "Clear rulers — remove all drawn rulers"},
    "TT_PLAY_PAUSE2":  {"ko": "재생 / 일시정지",     "en": "Play / Pause"},
    "TT_REWIND_STOP":  {"ko": "처음으로 되감기 + 정지", "en": "Rewind + stop"},
    "TT_CACHE_CLEAR":  {"ko": "프레임 캐시 비우기",  "en": "Clear frame cache"},

    # v2.992.beta-5: 단면 렌더 클립 방향
    "LBL_CLIP_SIDE":   {"ko": "<b>클립:</b>",        "en": "<b>Clip:</b>"},

    # v2.992.beta-5: mds_dialog 잔여 라벨
    "MD_NO_CHECKED":   {"ko": "체크된 데이터가 없습니다",      "en": "No checked data"},
    "MD_TREE_HINT":    {"ko": "(좌측 트리에서 체크하세요)",    "en": "(check items in the left tree)"},
    "MD_NO_DATA_TAB":  {"ko": "데이터 없음",                  "en": "No data"},
    "MD_HT_STD":       {"ko": "[열처리 표준 / 설명]",         "en": "[Heat-treat standard / notes]"},
    "MD_COL_MFG":      {"ko": "제조사",                       "en": "Mfg"},
    "MD_COL_MACHINE":  {"ko": "장비",                         "en": "Machine"},
    "MD_COL_POST":     {"ko": "후처리",                       "en": "Post"},
    "MD_COL_ELONG":    {"ko": "연신율\n%",                    "en": "Elong\n%"},
    "MD_COL_HARD":     {"ko": "경도\nHV",                     "en": "Hard\nHV"},

    # v2.992.beta-5: mds_dialog UI 라벨/버튼/상태 추가
    "MD_TAB_VENDOR":   {"ko": "🏭 제조사별 차이",             "en": "🏭 Vendor differences"},
    "MD_APP":          {"ko": "응용 분야",                    "en": "Applications"},
    "MD_PDF_ATTACH":   {"ko": "📎 로컬 PDF 첨부",             "en": "📎 Attach local PDF"},
    "MD_UNVERIFIED":   {"ko": "(미검증)",                     "en": "(unverified)"},
    "MD_LOCAL_OK":     {"ko": "✓ 로컬 OK",                    "en": "✓ Local OK"},
    "MD_FILE_MISSING": {"ko": "✗ 파일 없음",                  "en": "✗ File missing"},
    "MD_BTN_OPEN":     {"ko": "📂 열기",                      "en": "📂 Open"},
    "MD_EXTERNAL_URL": {"ko": "(외부 URL)",                   "en": "(external URL)"},
    "MD_BTN_COPY":     {"ko": "📋 복사",                      "en": "📋 Copy"},
    "MD_NO_REF":       {"ko": "(reference 없음)",             "en": "(no references)"},
    # v2.992.beta-5 hotfix5: MDS - data rows + radio buttons not previously wrapped
    "MD_CATEGORY":     {"ko": "카테고리: {cat}",              "en": "Category: {cat}"},
    "MD_BASIC_DENSITY":{"ko": "밀도",                          "en": "Density"},
    "MD_BASIC_MELT":   {"ko": "녹는점",                        "en": "Melting"},
    "MD_BASIC_MAG":    {"ko": "자성",                          "en": "Magnetic"},
    "MD_BASIC_YOUNGS": {"ko": "영률 (E)",                     "en": "Youngs (E)"},
    "MD_BASIC_POISSON":{"ko": "포아송 비",                     "en": "Poisson ratio"},
    "MD_BASIC_THERMK": {"ko": "열전도율",                      "en": "Thermal cond."},
    "MD_BASIC_CP":     {"ko": "비열 (Cp)",                    "en": "Specific heat (Cp)"},
    "MD_BASIC_CTE":    {"ko": "열팽창 (CTE)",                 "en": "Thermal expansion (CTE)"},
    "MD_HT_UTS":       {"ko": "인장강도 (UTS)",               "en": "Tensile (UTS)"},
    "MD_HT_YS":        {"ko": "항복강도 (YS, 0.2%)",          "en": "Yield (YS, 0.2%)"},
    "MD_HT_ELONG":     {"ko": "연신율 (Elongation)",          "en": "Elongation"},
    "MD_HT_HARD":      {"ko": "경도",                          "en": "Hardness"},
    "MD_HT_RA":        {"ko": "표면조도 Ra (μm)",             "en": "Surface roughness Ra (μm)"},
    "MD_RADIO_ELONG":    {"ko": "연신율 (%)",                 "en": "Elongation (%)"},
    "MD_RADIO_ELONG_XY": {"ko": "연신율 XY (%)",              "en": "Elongation XY (%)"},
    "MD_RADIO_ELONG_Z":  {"ko": "연신율 Z (%)",               "en": "Elongation Z (%)"},
    "MD_RADIO_HARD":     {"ko": "경도 (HV)",                  "en": "Hardness (HV)"},
    "MD_RADIO_RA":       {"ko": "표면조도 (μm)",              "en": "Roughness (μm)"},
    "MD_COL_TDS":        {"ko": "TDS",                        "en": "TDS"},
    "MD_CAT_FILTER":     {"ko": "<b>카테고리:</b>",            "en": "<b>Category:</b>"},
    "MD_CAT_ALL":        {"ko": "전체",                        "en": "All"},
    "MD_REPORT_BTN":     {"ko": "📊 선택 entry로 보고서 생성",
                          "en": "📊 Generate report from selected entries"},
    "MD_REPORT_NONE":    {"ko": "선택된 entry 없음",
                          "en": "No entries selected"},
    "MD_REPORT_NONE_MSG":{"ko": "보고서를 만들 entry를 먼저 좌측 트리에서 체크하세요.",
                          "en": "Check at least one entry in the tree before generating a report."},
    "MD_REPORT_SAVE_TITLE":{"ko": "보고서 저장 위치",
                            "en": "Save report as"},
    "MD_COL_ELONG":      {"ko": "연신율\nXY/Z %",             "en": "Elong\nXY/Z %"},

    # ── v2.992.beta-5: 외부 dialog 번역 키 ──
    # fixing_dialog (FX_*)
    "FX_TITLE":            {"ko": "고급 Fixing (v2.916 hotfix2)", "en": "Advanced Fixing"},
    "FX_DIAG_HEADER":      {"ko": "<b>◆ 진단 결과 + 항목별 Fix</b>", "en": "<b>◆ Diagnosis + Per-item Fix</b>"},
    "FX_LOG_HEADER":       {"ko": "<b>◆ 실행 로그</b>",        "en": "<b>◆ Execution Log</b>"},
    "FX_CTRL_HEADER":      {"ko": "◆ Fixing 컨트롤",            "en": "◆ Fixing Controls"},
    "FX_BTN_DIAG":         {"ko": "🔍 진단",                    "en": "🔍 Diagnose"},
    "FX_BTN_ALL":          {"ko": "⚡ 통합 Fixing",              "en": "⚡ Unified Fixing"},
    "FX_BTN_APPLY":        {"ko": "✓ 적용",                     "en": "✓ Apply"},
    "FX_STA_IDLE":         {"ko": "대기 중",                    "en": "Idle"},
    "FX_STA_DIAG":         {"ko": "진단 중...",                 "en": "Diagnosing..."},
    "FX_STA_DIAG_DONE":    {"ko": "진단 완료",                  "en": "Diagnosis complete"},
    "FX_STA_FIX_DONE":     {"ko": "완료",                       "en": "Complete"},
    "FX_STA_FAIL":         {"ko": "실패",                       "en": "Failed"},
    "FX_TABLE_COL":        {"ko": "항목,값,상태,동작",          "en": "Item,Value,Status,Action"},
    "FX_NO_RESULT_TITLE":  {"ko": "결과 없음",                  "en": "No result"},
    "FX_NO_RESULT_MSG":    {"ko": "먼저 Fixing 실행하세요.",    "en": "Run Fixing first."},
    "FX_APPLY_TITLE":      {"ko": "Fixing 적용",                "en": "Fixing applied"},
    "FX_APPLY_FAIL":       {"ko": "적용 실패",                  "en": "Apply failed"},

    # mds_dialog (MD_*)
    "MD_CMP_ITEM":         {"ko": "<b>비교 항목</b>",           "en": "<b>Comparison Item</b>"},
    "MD_MAT":              {"ko": "<b>재료:</b>",               "en": "<b>Material:</b>"},
    "MD_BASIC_PHYS":       {"ko": "기본 물리 / 열적 (열처리 무관)", "en": "Basic Physical / Thermal (heat-treat agnostic)"},
    "MD_HEAT_TREAT":       {"ko": "◆ 열처리 별 기계적 물성 + 표면조도", "en": "◆ Mechanical Properties + Surface Roughness by Heat Treatment"},
    "MD_NO_HEAT":          {"ko": "(열처리 데이터 없음)",       "en": "(No heat-treatment data)"},
    "MD_VENDORS_OFFICIAL": {"ko": "공식 지원 회사 (체크리스트)", "en": "Official Vendors (checklist)"},
    "MD_VENDORS_EXTRA":    {"ko": "<b>추가 지원사:</b>",        "en": "<b>Additional vendors:</b>"},
    "MD_COMP":             {"ko": "화학 조성 (% by weight)",    "en": "Chemical Composition (% by weight)"},
    "MD_REF":              {"ko": "참고 자료 (TDS / 논문)",     "en": "References (TDS / papers)"},
    "MD_NO_DATA":          {"ko": "데이터 없음",                "en": "No data"},
    "MD_PROP_HEADER":      {"ko": "<b>물성 데이터</b>",         "en": "<b>Properties</b>"},
    "MD_DENSITY":          {"ko": "밀도",                       "en": "Density"},
    "MD_E":                {"ko": "탄성률 E",                   "en": "Young's modulus E"},
    "MD_MELT":             {"ko": "녹는점",                     "en": "Melting point"},
    "MD_CTE":              {"ko": "열팽창",                     "en": "CTE"},
    "MD_HARD":             {"ko": "경도",                       "en": "Hardness"},
    "MD_TENSILE":          {"ko": "인장",                       "en": "Tensile"},
    "MD_VENDOR_VIEW":      {"ko": "벤더 보기",                  "en": "View vendor"},

    # analytics_dialog (AN_*)
    "AN_HEADER":           {"ko": "◆ 메시 분석 결과",           "en": "◆ Mesh Analysis Result"},
    "AN_WT_OK":            {"ko": "✅ Watertight (열린 엣지 없음)", "en": "✅ Watertight (no open edges)"},
    "AN_AUTO_FIX":         {"ko": "✓ 자동 보정:",               "en": "✓ Auto-fix:"},
    "AN_TAB_GEO":          {"ko": "📐 기하",                    "en": "📐 Geometry"},
    "AN_TAB_INT":          {"ko": "🔧 무결성",                  "en": "🔧 Integrity"},
    "AN_TAB_TIME":         {"ko": "⏱ 빌드 시간",                "en": "⏱ Build Time"},

    # pyvista_window (PW_*)
    "PW_VIEW":             {"ko": "시점",                       "en": "View"},
    "PW_VIS":              {"ko": "가시성",                     "en": "Visibility"},
    "PW_COLOR_MODE":       {"ko": "색상 모드",                  "en": "Color Mode"},
    "PW_SUPPORT_DEG":      {"ko": "Support 임계각 (°)",         "en": "Support threshold (°)"},

    # v2.992.beta-5 hotfix5: 분석결과 패널 (build_report_text + left/right panel)
    "RPT_LEFT_EMPTY":      {"ko": "(STL 파일을 열어주세요. Ctrl+O)",
                              "en": "(Please open an STL file. Ctrl+O)"},
    "RPT_LEFT_FAIL":       {"ko": "좌측 갱신 실패",
                              "en": "Left panel update failed"},
    "RPT_RIGHT_FAIL":      {"ko": "우측 갱신 실패",
                              "en": "Right panel update failed"},
    "RPT_TITLE":           {"ko": "STL Analyzer 분석 보고서",
                              "en": "STL Analyzer Analysis Report"},
    "RPT_TIMESTAMP":       {"ko": "작성 시각",                  "en": "Created"},
    "RPT_FILE":            {"ko": "파일",                        "en": "File"},
    "RPT_PATH":            {"ko": "경로",                        "en": "Path"},
    "RPT_FILESIZE":        {"ko": "파일 크기",                  "en": "File size"},
    "RPT_FORMAT":          {"ko": "포맷",                        "en": "Format"},
    "RPT_BACKEND":         {"ko": "백엔드",                      "en": "Backend"},
    "RPT_SEC_GEOMETRY":    {"ko": "[ 1. 기하 / 메시 ]",          "en": "[ 1. Geometry / Mesh ]"},
    "RPT_TRIANGLE_CNT":    {"ko": "삼각형 수",                   "en": "Triangle count"},
    "RPT_BBOX_DIM":        {"ko": "BBox W×D×H",                  "en": "BBox W x D x H"},
    "RPT_BBOX_X_RANGE":    {"ko": "BBox X 범위",                 "en": "BBox X range"},
    "RPT_BBOX_Y_RANGE":    {"ko": "BBox Y 범위",                 "en": "BBox Y range"},
    "RPT_BBOX_Z_RANGE":    {"ko": "BBox Z 범위",                 "en": "BBox Z range"},
    "RPT_DIAGONAL":        {"ko": "대각선",                      "en": "Diagonal"},
    "RPT_VOLUME":          {"ko": "부피",                        "en": "Volume"},
    "RPT_SURFACE_AREA":    {"ko": "표면적",                      "en": "Surface area"},
    "RPT_AVG_TRI_AREA":    {"ko": "평균 tri 면적",               "en": "Avg triangle area"},
    "RPT_SEC_INTEGRITY":   {"ko": "[ 2. 무결성 (Magics 호환) ]", "en": "[ 2. Integrity (Magics-compat) ]"},
    "RPT_WATERTIGHT":      {"ko": "Watertight",                  "en": "Watertight"},
    "RPT_BAD_EDGES":       {"ko": "Bad edges (합)",              "en": "Bad edges (total)"},
    "RPT_OPEN_EDGES":      {"ko": "Open edges",                  "en": "Open edges"},
    "RPT_NON_MANIFOLD":    {"ko": "Non-manifold",                "en": "Non-manifold"},
    "RPT_HOLES":           {"ko": "Holes (loops)",               "en": "Holes (loops)"},
    "RPT_SHELLS":          {"ko": "Shells",                      "en": "Shells"},
    "RPT_AUTO_FIXES":      {"ko": "자동 수정",                   "en": "Auto fixes"},
    "RPT_WARNINGS":        {"ko": "경고",                        "en": "Warnings"},
    "RPT_SEC_WALL":        {"ko": "[ 3. 벽 두께 통계 ]",         "en": "[ 3. Wall thickness ]"},
    "RPT_THIN_WALLS":      {"ko": "얇은벽 (≤1mm)",               "en": "Thin walls (<=1mm)"},
    "RPT_SEC_MACHINE":     {"ko": "[ 4. 장비 / Plate ]",         "en": "[ 4. Machine / Plate ]"},
    "RPT_DEVICE":          {"ko": "기기",                        "en": "Device"},
    "RPT_PLATE_AREA":      {"ko": "Plate 면적",                  "en": "Plate area"},
    "RPT_BUILD_DIR":       {"ko": "빌드 방향",                   "en": "Build direction"},
    "RPT_SEC_MATERIAL":    {"ko": "[ 5. 재료 / 부품 무게 ]",     "en": "[ 5. Material / Part Weight ]"},
    "RPT_MATERIAL":        {"ko": "재료",                        "en": "Material"},
    "RPT_DENSITY":         {"ko": "밀도",                        "en": "Density"},
    "RPT_SAFETY_MARGIN":   {"ko": "안전마진",                    "en": "Safety margin"},
    "RPT_PART_VOLUME":     {"ko": "부품 부피",                   "en": "Part volume"},
    "RPT_PART_WEIGHT":     {"ko": "부품 무게",                   "en": "Part weight"},
    "RPT_SEC_BUILD":       {"ko": "[ 6. 빌드 envelope / 분말 ]", "en": "[ 6. Build envelope / Powder ]"},
    "RPT_PART_Z_HEIGHT":   {"ko": "부품 Z 높이",                 "en": "Part Z height"},
    "RPT_EDM_MARGIN":      {"ko": "EDM 마진",                    "en": "EDM margin"},
    "RPT_BUILD_HEIGHT":    {"ko": "빌드 높이",                   "en": "Build height"},
    "RPT_BUILD_VOLUME":    {"ko": "빌드 부피",                   "en": "Build volume"},
    "RPT_PACKING_RATIO":   {"ko": "패킹률",                      "en": "Packing ratio"},
    "RPT_POWDER_NEEDED":   {"ko": "필요 분말",                   "en": "Powder required"},

    # v2.992.beta-5 hotfix5: 콘솔 라벨 + tooltip
    "CONSOLE_LBL":         {"ko": "<b style='color:#1a3a6a;'>📋 콘솔:</b>",
                              "en": "<b style='color:#1a3a6a;'>📋 Console:</b>"},
    "CONSOLE_VERBOSE_TIP": {"ko": "체크하면 파일 로드/UI 조작/clipping/렌더모드/시점/멀티뷰 등 각 동작에 timestamp + 카테고리 + 경과시간 상세 출력",
                              "en": "If checked, prints detailed timestamp + category + elapsed time for each action: file load / UI / clipping / render mode / view / multi-view, etc."},

    # v2.992.beta-5 hotfix7: Help / 3D standalone / context menu / recent / progress
    "HELP_DIAGNOSTIC_ZIP": {"ko": "🛠 진단 로그 zip 생성 (Beta)",
                              "en": "🛠 Create diagnostic log zip (Beta)"},
    "MSG_DIAG_ZIP_FAIL":   {"ko": "진단 zip 실패",            "en": "Diagnostic zip failed"},
    "MSG_DIAG_ZIP_DONE":   {"ko": "진단 zip 생성 완료",        "en": "Diagnostic zip created"},
    "MSG_DIAG_ZIP_MAIN_MISSING":{"ko": "main.collect_diagnostic_zip 함수를 찾을 수 없습니다.\n수동 수집: EXE 옆 stl_analyzer*.log 파일들을 zip 으로 묶어주세요.",
                              "en": "main.collect_diagnostic_zip function not found.\nManual collection: zip the stl_analyzer*.log files next to the EXE."},
    "MSG_DIAG_ZIP_BODY":   {"ko": "생성된 파일:\n  {path}\n\n이 zip 을 개발자에게 보내주세요\n(GitHub Issue / 이메일 첨부).\n\n포함 내용:\n  - stl_analyzer.log (운영 로그)\n  - stl_analyzer_crash.log (uncaught 예외)\n  - stl_analyzer_fault.log (native crash)\n  - 시스템 정보 (OS/Python/GPU)",
                              "en": "Created file:\n  {path}\n\nPlease send this zip to the developer\n(GitHub Issue / email attachment).\n\nContents:\n  - stl_analyzer.log (operation log)\n  - stl_analyzer_crash.log (uncaught exceptions)\n  - stl_analyzer_fault.log (native crash)\n  - System info (OS/Python/GPU)"},

    # 3D standalone dialog title + status hint (description updated)
    "WIN_3D_STANDALONE":   {"ko": "3D 단독창 — {fname}",
                              "en": "3D standalone - {fname}"},
    "STA_3D_STANDALONE_OPENED":{"ko": "3D 단독창 — 좌측: 3D 뷰 + Clipping/가시성 | 우측: 시점/색상 모드/LOD | 단축키: X / Y / Z / I (ISO)",
                              "en": "3D standalone - Left: 3D view + Clipping/Visibility | Right: View/Color mode/LOD | Shortcuts: X / Y / Z / I (ISO)"},

    # context menu (3D preview right-click)
    "CTX_BBOX_TOGGLE":     {"ko": "BBox 토글",                "en": "Toggle BBox"},
    "CTX_PLATE_TOGGLE":    {"ko": "플레이트 토글",            "en": "Toggle plate"},
    "CTX_ALPHA_TOGGLE":    {"ko": "반투명 토글",              "en": "Toggle transparency"},
    "CTX_3D_STANDALONE":   {"ko": "🪟 3D 단독창",             "en": "🪟 Open 3D standalone"},

    # recent files menu
    "MNU_RECENT_EMPTY":    {"ko": "(없음)",                   "en": "(none)"},
    "MNU_RECENT_CLEAR":    {"ko": "최근 파일 비우기",         "en": "Clear recent files"},

    # progress dialogs
    "PB_PRERENDER":        {"ko": "사전 렌더 진행 중...",     "en": "Pre-rendering..."},
    "BTN_CANCEL_PLAIN":    {"ko": "취소",                     "en": "Cancel"},

    # v2.992.beta-5 hotfix12: plate shape + build envelope + skip indicators
    "PLATE_SHAPE_SQUARE":  {"ko": "사각",                     "en": "square"},
    "PLATE_SHAPE_ROUND":   {"ko": "원형",                     "en": "round"},
    "RPT_LARGE_SKIP":      {"ko": "(대용량 skip)",            "en": "(large-mesh skip)"},
    "BUILD_HEIGHT_BREAKDOWN":{"ko": "부품 {part:.1f} + EDM {edm:.1f}",
                              "en": "part {part:.1f} + EDM {edm:.1f}"},
    "BUILD_HEIGHT_BREAKDOWN_IN":{"ko": "부품 {part:.2f} + EDM {edm:.2f}",
                                  "en": "part {part:.2f} + EDM {edm:.2f}"},
    "STD_CLIP_HINT":       {"ko": "(단축키: X / Y / Z 모드 순환 — Off → 교선만 → Clip+ → Clip-, Shift+X/Y/Z 리셋, Esc 모두 Off)",
                              "en": "(Shortcuts: X / Y / Z cycle modes - Off -> Contour -> Clip+ -> Clip-, Shift+X/Y/Z reset, Esc all Off)"},
    "STD_OPENED_LOG":      {"ko": "3D 단독창 열림",           "en": "3D standalone opened"},
    "STD_BTN_CLIP":        {"ko": "Clip",                     "en": "Clip"},
    "STD_BTN_OUTLINE":     {"ko": "외곽선",                   "en": "Outline"},
    "STD_BTN_AXIS":        {"ko": "축",                       "en": "Axis"},
    "STD_BTN_ORTHO":       {"ko": "Ortho",                    "en": "Ortho"},
    "STD_BTN_LOD":         {"ko": "LOD",                      "en": "LOD"},
    # Short clip mode labels for axis row buttons (compact 44px buttons)
    "CLIP_MODE_SHORT_OFF":     {"ko": "Off",         "en": "Off"},
    "CLIP_MODE_SHORT_CONTOUR": {"ko": "교선",        "en": "Cont"},
    "CLIP_MODE_SHORT_CLIP_PLUS":  {"ko": "C+",       "en": "C+"},
    "CLIP_MODE_SHORT_CLIP_MINUS": {"ko": "C−",       "en": "C−"},
    # v2.992.beta-5 hotfix12: Section measure mode toggle button (replaces right-click)
    "BTN_MEASURE":           {"ko": "📏 측정",          "en": "📏 Measure"},
    "TT_MEASURE_TOGGLE":     {"ko": "측정 모드 — ON: 좌클릭 2회로 거리 측정. 우클릭 = 모드 해제 (라벨 유지).",
                                "en": "Measure mode - ON: left-click 2x to measure. Right-click = release mode (keep labels)."},
    "BTN_ARC":               {"ko": "⌒ 원호 R",         "en": "⌒ Arc R"},
    "TT_ARC_TOGGLE":         {"ko": "원호 반경 측정 — ON: 좌클릭 3점으로 반경 계산. 우클릭 = 모드 해제 (라벨 유지).",
                                "en": "Arc R - ON: left-click 3 pts for radius. Right-click = release mode (keep labels)."},
    "STA_MEASURE_ON":        {"ko": "측정 모드 ON — 좌클릭 2회로 거리 측정 (우클릭/Esc 해제)",
                                "en": "Measure mode ON - left-click 2x to measure (right-click/Esc release)"},
    "STA_MEASURE_OFF":       {"ko": "측정 모드 OFF",
                                "en": "Measure mode OFF"},
    "STA_ARC_ON":            {"ko": "원호 측정 ON — 좌클릭 3점으로 원호 반경 계산 (우클릭/Esc 해제)",
                                "en": "Arc mode ON - left-click 3 points for arc radius (right-click/Esc release)"},
    "STA_ARC_OFF":           {"ko": "원호 측정 OFF",
                                "en": "Arc mode OFF"},
    # v2.992.beta-5 hotfix14: 측정/원호 제거 결과 메시지 i18n
    "STA_RULER_CLEARED":     {"ko": "측정/원호 {n}개 제거",
                                "en": "Cleared {n} measurement(s)"},
    "STA_DLG_RULER_CLEARED": {"ko": "단독창 Ruler/Arc {n}개 제거",
                                "en": "Standalone: cleared {n} measurement(s)"},
    # v2.992.beta-5 hotfix14: 우클릭으로 측정/원호 모드 해제 (라벨 유지)
    "STA_MEASURE_RELEASED":  {"ko": "측정/원호 모드 해제 — 라벨은 그대로 유지 (🗑 로 전체 제거)",
                                "en": "Measure/Arc mode released — labels kept (use 🗑 to clear)"},
    # v2.992.beta-5 hotfix15: 3D 단독창 사전 렌더 한국어 leak fix
    "TT_SR_PRERENDER":       {"ko": "모든 step 위치의 clipped mesh + feature edges 를\n프레임 캐시에 저장. 재생 시 actor 만 swap → 부드러움.",
                                "en": "Pre-render clipped mesh + feature edges for every step position.\nPlayback swaps actor only — smooth."},
    "STA_SR_BUILDING":       {"ko": "🎞 사전 렌더 중... {i}/{n}",
                                "en": "🎞 Pre-rendering... {i}/{n}"},
    "STA_SR_GPU_BUILDING":   {"ko": "🎞 GPU 사전 렌더... {i}/{n}",
                                "en": "🎞 GPU pre-rendering... {i}/{n}"},
    "LBL_SR_CACHE_OK":       {"ko": "✓ 캐시: {n} ({ax}축, {mode}, Clip{side})",
                                "en": "✓ Cache: {n} ({ax} axis, {mode}, Clip{side})"},
    "STA_SR_DONE":           {"ko": "✓ 사전 렌더 완료 ({el}s) — ▶ 부드러운 재생",
                                "en": "✓ Pre-render done ({el}s) — ▶ smooth playback"},
    # v2.992.beta-5 hotfix18: Slice Render 영역 한국어 leak 추가 정리
    "STA_SR_AXIS_RANGE":     {"ko": "{ax} 축 [{lo} ~ {hi}] mm",
                                "en": "{ax} axis [{lo} ~ {hi}] mm"},
    "STA_SR_FRAME_CACHE":    {"ko": "▶ {ax}{sign} = {v}mm [{n}/{total}] (캐시)",
                                "en": "▶ {ax}{sign} = {v}mm [{n}/{total}] (cache)"},
    "STA_SR_FRAME_REALTIME": {"ko": "▶ {ax}{sign} = {v}mm (실시간)",
                                "en": "▶ {ax}{sign} = {v}mm (realtime)"},
    "STA_SR_STARTED":        {"ko": "▶ {ax}{sign} 시작",
                                "en": "▶ {ax}{sign} started"},
    # v2.992.beta-5 hotfix20: 잔존 lbl_status setText 한국어 leak 일괄 정리 (12건)
    "STA_MATERIAL_APPLIED":  {"ko": "재료: {name}, 밀도 {d} g/cm³",
                                "en": "Material: {name}, density {d} g/cm³"},
    "STA_GRID_PREVIEW_FAIL": {"ko": "격자 미리보기 제거 실패: {e}",
                                "en": "Grid preview remove failed: {e}"},
    "STA_HOLE_BOUNDARY":     {"ko": "Hole 경계 {n}개 검출 (빨간선 표시)",
                                "en": "{n} hole boundaries detected (red lines)"},
    "STA_STL_SAVED":         {"ko": "STL 저장: {path}",
                                "en": "STL saved: {path}"},
    "STA_REPORT_SAVED":      {"ko": "보고서 저장: {path}",
                                "en": "Report saved: {path}"},
    "STA_SUPPORT_SAVED":     {"ko": "Support 저장: {path}",
                                "en": "Support saved: {path}"},
    "STA_BUILD_DIR_SELECTED":{"ko": "빌드 방향 선택: {axis} (파일 로드 후 적용)",
                                "en": "Build direction: {axis} (applied after file load)"},
    "STA_UNDO":              {"ko": "실행 취소: {op}",
                                "en": "Undo: {op}"},
    "STA_REDO":              {"ko": "다시 실행: {op}",
                                "en": "Redo: {op}"},
    "STA_VIEW_APPLIED":      {"ko": "시점 V{n} ({kind} yaw={yaw}°, plate-center)",
                                "en": "View V{n} ({kind} yaw={yaw}°, plate-center)"},
    "STA_RENDER_MODE":       {"ko": "렌더 모드: {mode}",
                                "en": "Render mode: {mode}"},
    "STA_SCREENSHOT_SAVED":  {"ko": "스크린샷 저장: {path}",
                                "en": "Screenshot saved: {path}"},
    # 메인 슬라이스 사전 렌더 (Z 범위 dialog)
    "PR_PART_Z_RANGE":       {"ko": "<b>부품 Z 범위:</b> {lo} ~ {hi} mm (높이 {h} mm)",
                                "en": "<b>Part Z range:</b> {lo} ~ {hi} mm (height {h} mm)"},
    "TT_PR_Z_START_MIN":     {"ko": "시작 Z 를 부품 z_min ({v}) 로",
                                "en": "Set start Z to part z_min ({v})"},
    "TT_PR_Z_END_MAX":       {"ko": "끝 Z 를 부품 z_max ({v}) 로",
                                "en": "Set end Z to part z_max ({v})"},
    "LBL_STEP_MM_B":         {"ko": "<b>Step (mm):</b>",
                                "en": "<b>Step (mm):</b>"},
    "PR_INVALID_Z":          {"ko": "⚠ 끝 Z &gt; 시작 Z, Step &gt; 0 필요",
                                "en": "⚠ End Z &gt; Start Z, Step &gt; 0 required"},
    "PR_PREVIEW_COUNT":      {"ko": "<b>📊 예상: {n} 프레임</b> (범위 {rng} mm, 메모리 약 {mb} MB)",
                                "en": "<b>📊 Estimated: {n} frames</b> (range {rng} mm, ~{mb} MB)"},
    "MSG_ERROR_PREFIX":      {"ko": "오류: {e}",
                                "en": "Error: {e}"},
    "PR_CONFIRM_LARGE":      {"ko": "<b>{n} 프레임</b> 렌더링 예정입니다.<br>(z {lo} ~ {hi}, Step {st} mm)<br><br>메모리/시간 소요가 큽니다. 계속할까요?",
                                "en": "<b>{n} frames</b> will be rendered.<br>(z {lo} ~ {hi}, Step {st} mm)<br><br>This uses significant memory/time. Continue?"},
    "STA_PR_CANCELLED":      {"ko": "사전 렌더 취소 ({n} 프레임만 캐시됨)",
                                "en": "Pre-render cancelled ({n} frames cached)"},
    "STA_PR_DONE":           {"ko": "사전 렌더 완료 — {n} 프레임 / {el}s",
                                "en": "Pre-render done — {n} frames / {el}s"},
    "STA_ANIM_PLAYING":      {"ko": "단면 애니메이션 재생 ({speed})",
                                "en": "Slice animation playing ({speed})"},
    # 단독창 Clipping 라벨/툴팁
    "TT_CLIP_OUTLINE_WIDTH": {"ko": "단면 교선 (clip outline) 의 선 두께 (0.5 ~ 10.0)",
                                "en": "Clip outline line width (0.5 ~ 10.0)"},
    "TT_CLIP_AXIS_LBL":      {"ko": "{ax}축 — 단축키: {ax} (모드 순환), Shift+{ax} (리셋)",
                                "en": "{ax} axis — hotkeys: {ax} (cycle mode), Shift+{ax} (reset)"},
    "TT_CLIP_AXIS_MODE":     {"ko": "{ax}축 모드: {mode}",
                                "en": "{ax} axis mode: {mode}"},
    "TT_CLIP_VAL_DOWN":      {"ko": "{ax} 값 감소 (Δ step)",
                                "en": "{ax} value down (Δ step)"},
    "TT_CLIP_VAL_UP":        {"ko": "{ax} 값 증가 (Δ step)",
                                "en": "{ax} value up (Δ step)"},
    "TT_CLIP_VAL_INPUT":     {"ko": "{ax} 값 직접 입력 ([{lo} ~ {hi}] mm)",
                                "en": "{ax} value direct input ([{lo} ~ {hi}] mm)"},
    "TT_CLIP_AXIS_RESET":    {"ko": "{ax}축 리셋 (Shift+{ax})",
                                "en": "{ax} axis reset (Shift+{ax})"},
    "STA_STD_AXIS_MODE":     {"ko": "[3D 단독] {ax}축 → {mode}",
                                "en": "[Standalone 3D] {ax} axis → {mode}"},
    "STA_VIS_TOGGLE":        {"ko": "가시성: {key} = {on}",
                                "en": "Visibility: {key} = {on}"},
    # v2.992.beta-5 hotfix16: CuPy 제거 후 backend 라벨 (NVIDIA GPU → Numba JIT)
    "STA_BACKEND_NUMBA":     {"ko": "🟢 Numba {ver}",
                                "en": "🟢 Numba {ver}"},
    "STA_BACKEND_NUMPY":     {"ko": "⚪ NumPy CPU",
                                "en": "⚪ NumPy CPU"},
    "TT_BACKEND_NUMBA":      {"ko": "Numba JIT 가속 활성 ({ver})\nslicing / orientation / downface 3~10× 가속\nVTK GPU paths (clipping) 는 항상 활성\n← 클릭: 상세 정보",
                                "en": "Numba JIT acceleration active ({ver})\nslicing / orientation / downface 3-10x speedup\nVTK GPU paths (clipping) always active\n← Click: details"},
    "TT_BACKEND_NUMPY":      {"ko": "Numba 미설치 — pure NumPy 사용 중\n원인: {reason}\n해결: pip install numba (선택, 가속 ↑)\n← 클릭: 상세 정보",
                                "en": "Numba not installed - using pure NumPy\nReason: {reason}\nFix: pip install numba (optional, faster)\n← Click: details"},
    "TT_BACKEND_FAIL":       {"ko": "Backend 상태 확인 실패: {e}",
                                "en": "Backend status check failed: {e}"},
    "BACKEND_DLG_TITLE":     {"ko": "가속 백엔드 정보",
                                "en": "Accelerator Backend Info"},
    "BACKEND_DLG_NUMBA_BENEFIT": {"ko": "<b>가속 효과:</b><br>&nbsp;&nbsp;slicing 3~5×, downface 4×, 6축 orientation 4× 가속",
                                  "en": "<b>Acceleration:</b><br>&nbsp;&nbsp;slicing 3-5x, downface 4x, 6-axis orientation 4x faster"},
    "BACKEND_DLG_NUMBA_FAIL":{"ko": "<b>Numba 비활성 원인:</b> {reason}",
                                "en": "<b>Numba inactive:</b> {reason}"},
    "BACKEND_DLG_INSTALL_HINT": {"ko": "<b>Numba 설치 (선택):</b><br>&nbsp;&nbsp;<code>pip install numba</code>",
                                  "en": "<b>Install Numba (optional):</b><br>&nbsp;&nbsp;<code>pip install numba</code>"},
    "BACKEND_DLG_VTK_NOTE":  {"ko": "<b>VTK GPU paths:</b> 항상 활성 (clipping / cutting / decimation 등 GPU 가속 — backend 무관)",
                                "en": "<b>VTK GPU paths:</b> always active (clipping/cutting/decimation use GPU regardless)"},
    "BACKEND_DLG_ENV_HEADER":{"ko": "<b>환경 변수:</b>",
                                "en": "<b>Environment variables:</b>"},
    "BACKEND_DLG_FAIL":      {"ko": "백엔드 상태 표시 실패",
                                "en": "Backend status display failed"},
    # v2.992.beta-5 hotfix13: reload Korean leaks
    "MSG_RELOAD_NONE":       {"ko": "리로드할 파일이 없습니다. 먼저 STL 파일을 열어주세요.",
                                "en": "No file to reload. Open an STL file first."},
    "MSG_FILE_NOT_EXIST":    {"ko": "파일이 존재하지 않음:\n{path}",
                                "en": "File does not exist:\n{path}"},
    "STA_RELOAD_NOW":        {"ko": "리로드: {name}",
                                "en": "Reload: {name}"},
    "STA_PCA_RESET_ROT":     {"ko": "PCA 정렬 후 회전 0/0/0 재정의 — 빌드 방향 기준",
                                "en": "PCA alignment - rotation re-baselined to 0/0/0"},
    # v2.992.beta-5 hotfix14: leftover Korean leaks (screenshot)
    "STA_MAIN_3D_FROZEN":    {"ko": "❄ 메인 3D 동결 ({reason}) — 단독창 종료 또는 [복귀] 클릭",
                                "en": "❄ Main 3D frozen ({reason}) - close standalone or click [Resume]"},
    "STA_MAIN_3D_ACTIVE":    {"ko": "☀ 메인 3D 활성 ({reason})",
                                "en": "☀ Main 3D active ({reason})"},
    "SLC_CLOSED_LOOPS":      {"ko": "닫힘",                     "en": "Closed"},
    "SLC_OPEN_LOOPS":        {"ko": "열림",                     "en": "Open"},
    "REASON_STANDALONE_END": {"ko": "단독창 종료",              "en": "standalone closed"},
    "REASON_STANDALONE_3D":  {"ko": "3D 단독창 활성",           "en": "3D standalone active"},
    "REASON_USER":           {"ko": "사용자 명령",              "en": "user command"},

    # v2.992.beta-5 hotfix8: 종합 leak fix - critical user-visible labels/tooltips
    "LBL_LOAD_OPTIONS":    {"ko": "<b style='color:#1a3a6a;'>⚡ 로드 옵션:</b>",
                              "en": "<b style='color:#1a3a6a;'>⚡ Load options:</b>"},
    "LBL_F1_HELP":         {"ko": "<small style='color:#666;'>F1 도움말</small>",
                              "en": "<small style='color:#666;'>F1 Help</small>"},
    "TT_LOAD_FIX":         {"ko": "STL 로드 시 자동 퇴화 삼각형 제거 + 법선 보정\nv2.992.beta-5: 기본 OFF (필요 시 체크).\n100MB+ 에서는 끄면 5~30초 단축",
                              "en": "Auto-remove degenerate triangles + fix normals on STL load\nv2.992.beta-5: default OFF (check if needed).\nDisabling saves 5-30s on 100MB+ files"},
    "TT_LOAD_WATERTIGHT":  {"ko": "자동 watertight / open edges / non-manifold 검사",
                              "en": "Auto watertight / open edges / non-manifold check"},
    "TT_LOAD_PRECOMP":     {"ko": "Full STL edge 맵 백그라운드 사전계산",
                              "en": "Background pre-compute of full STL edge map"},
    "TT_LOAD_PREVIEW":     {"ko": "로드 직후 3D 메시 미리보기 렌더링",
                              "en": "Render 3D mesh preview right after load"},
    "TT_LOAD_MP":          {"ko": "2M+ tris 에서 후처리 multiprocessing (ndarray 유지)",
                              "en": "Multiprocessing post-process for 2M+ tris (ndarray preserved)"},
    "TT_LOD_TOGGLE":       {"ko": "메인 3D 미리보기에 LOD (Level-of-Detail) 적용\n체크 시 100k 폴리곤 초과 메시는 ratio 콤보 만큼 데시메이트\n→ 메인 UI 빠른 응답 (정밀도 약간 손실)",
                              "en": "Apply LOD (Level-of-Detail) to main 3D preview\nWhen checked, meshes over 100k polygons are decimated by the ratio combo\n-> faster main UI response (slight precision loss)"},
    "TT_LOD_RATIO":        {"ko": "메인 LOD 보존 비율 (0.1% ~ 70%)",
                              "en": "Main LOD retention ratio (0.1% to 70%)"},
    "TT_LOD_ALGO":         {"ko": "메인 LOD 알고리즘\nDec(정확) / QSMP(멀티스레드) / Clu(빠름, 퀄리티↓) / Vox(numpy) / Auto(크기별)",
                              "en": "Main LOD algorithm\nDec(accurate) / QSMP(multi-threaded) / Clu(fast, lower quality) / Vox(numpy) / Auto(size-adaptive)"},
    "TT_VIS_TOGGLE":       {"ko": "{label} 표시 토글",         "en": "Toggle {label} visibility"},
    "ERR_PYVISTA_LOAD":    {"ko": "3D 미리보기 — PyVista 로드 실패\n\n오류: {e}\n\n설치: uv pip install pyvista pyvistaqt vtk",
                              "en": "3D preview - PyVista load failed\n\nError: {e}\n\nInstall: uv pip install pyvista pyvistaqt vtk"},
    "ERR_MPL_LOAD":        {"ko": "단면 캔버스 — matplotlib 로드 실패\n\n오류: {e}\n\n설치: pip install matplotlib",
                              "en": "Section canvas - matplotlib load failed\n\nError: {e}\n\nInstall: pip install matplotlib"},

    # Render modes (3D preview color/render mode descriptions)
    "RM_FEATURE":          {"ko": "Feature Edges — dihedral ≥ 45° (선 굵기 2.0)",
                              "en": "Feature Edges - dihedral >= 45 deg (line width 2.0)"},
    "RM_SOFT":             {"ko": "Soft (Edge-Lit) — 부드러운 음영",
                              "en": "Soft (Edge-Lit) - soft shading"},
    "RM_SOLID":            {"ko": "Solid (Full STL) — 면 + 에지",
                              "en": "Solid (Full STL) - faces + edges"},
    "RM_SUPPORT":          {"ko": "Support (각도별) — overhang 색상 분류",
                              "en": "Support (by angle) - overhang color classification"},

    # Visibility labels (toggle buttons under 3D preview)
    "VIS_EDM":             {"ko": "EDM",                       "en": "EDM"},
    "VIS_PLATE":           {"ko": "플레이트",                  "en": "Plate"},
    "VIS_SLICE":           {"ko": "슬라이스",                  "en": "Slice"},
    "VIS_BBOX":            {"ko": "BBox",                      "en": "BBox"},
    "VIS_GRID":            {"ko": "그리드",                    "en": "Grid"},
    "VIS_ALPHA":           {"ko": "반투명",                    "en": "Transparency"},

    # Clip modes (mode dropdown in clipping bar)
    "CLIP_MODE_OFF":       {"ko": "Off",                       "en": "Off"},
    "CLIP_MODE_CONTOUR":   {"ko": "교선만",                    "en": "Contour only"},
    "CLIP_MODE_CLIP_PLUS": {"ko": "Clip+",                     "en": "Clip+"},
    "CLIP_MODE_CLIP_MINUS":{"ko": "Clip-",                     "en": "Clip-"},

    # LOD preset combo items
    "LOD_RATIO_70":        {"ko": "70% (얕은)",                "en": "70% (Light)"},
    "LOD_RATIO_30":        {"ko": "30% (기본)",                "en": "30% (Default)"},
    "LOD_RATIO_10":        {"ko": "10% (드래그)",              "en": "10% (Drag)"},
    "LOD_RATIO_3":         {"ko": "3% (초경량)",               "en": "3% (Ultra-light)"},
    "LOD_ALGO_AUTO":       {"ko": "Auto (메시 크기별, 기본)",  "en": "Auto (mesh-size adaptive, default)"},
    "LOD_ALGO_DECIMATE":   {"ko": "Decimate (정확, 느림)",     "en": "Decimate (accurate, slow)"},
    "LOD_ALGO_QUADRIC":    {"ko": "QuadricSMP (멀티스레드)",   "en": "QuadricSMP (multi-threaded)"},
    "LOD_ALGO_CLUSTERING": {"ko": "Clustering (가장 빠름)",    "en": "Clustering (fastest)"},
    "LOD_ALGO_VOXEL":      {"ko": "Voxel (numpy)",             "en": "Voxel (numpy)"},

    # Multi-view dialog panel headers
    "MV_PANE_TOP":         {"ko": "◆ Top (XY 단면, Z 평면)",   "en": "◆ Top (XY section, Z plane)"},
    "MV_PANE_FRONT":       {"ko": "◆ Front (XZ 단면, Y 평면)", "en": "◆ Front (XZ section, Y plane)"},
    "MV_PANE_SIDE":        {"ko": "◆ Side (YZ 단면, X 평면)",  "en": "◆ Side (YZ section, X plane)"},
    "MV_SLIDER_HEADER":    {"ko": "<b>◆ 슬라이더 (X/Y/Z)</b>",
                              "en": "<b>◆ Sliders (X/Y/Z)</b>"},
    "MV_WINDOW_TITLE":     {"ko": "Multi-View 단면 — {fname}",
                              "en": "Multi-view section - {fname}"},
    "MV_OPENED_STATUS":    {"ko": "Multi-view 단면 창 열림 (3D + XY/XZ/YZ 4-pane)",
                              "en": "Multi-view section opened (3D + XY/XZ/YZ 4-pane)"},
    "SL_STANDALONE_LBL":   {"ko": "단면 단독창 (고급)",
                              "en": "Slice standalone (advanced)"},

    # Box-zoom / matplotlib toolbar
    "STA_BOX_ZOOM_ON":     {"ko": "단면 Box Zoom ON  (드래그로 영역 선택)",
                              "en": "Section Box Zoom ON (drag to select area)"},
    "STA_BOX_ZOOM_OFF":    {"ko": "단면 Box Zoom OFF",
                              "en": "Section Box Zoom OFF"},
    "STA_SECT_ZOOM":       {"ko": "단면 줌 {label}",
                              "en": "Section zoom {label}"},
    "TT_RULER_HINT":       {"ko": "(우클릭 2회 = 새 ruler)",
                              "en": "(right-click 2x = new ruler)"},

    # Common dialog snippets
    "MSG_OPEN_STL_FIRST":  {"ko": "STL을 먼저 열어주세요",
                              "en": "Please open an STL first"},
    "MSG_GRID_QTY_1":      {"ko": "수량이 1이므로 배치할 항목이 없습니다.<br>",
                              "en": "Quantity is 1, nothing to lay out.<br>"},

    # 3D preview render-mode change status
    "STA_RENDER_RELEASED": {"ko": "{mode} 모드 해제됨",
                              "en": "{mode} mode released"},
}


def set_language(lang_code):
    """언어 변경 ('ko' 또는 'en'). 잘못된 코드는 ignored.

    Thread safety: main thread only (Qt UI initialization 시점).
    GIL 보호로 단순 read/write 는 atomic 하지만 multi-thread 패턴은 미지원.
    """
    global _current_lang
    if lang_code in ("ko", "en"):
        _current_lang = lang_code


def get_language():
    """현재 언어 코드 반환 (main thread only)."""
    return _current_lang


# v2.992.beta-5 W4: 누락 key 디버그 로그 — 중복 출력 방지용 set
_missing_keys_logged = set()


def tr(key, **kwargs):
    """번역 lookup. 키 없으면 키 자체 반환 (fallback).
    {param} 포함 시 .format(**kwargs) 호출.

    v2.992.beta-5 W4: 누락 key 는 첫 1회 디버그 로그 출력 (런타임 silent fail 가시화).
    """
    s = _STRINGS.get(key)
    if s is None:
        # v2.992.beta-5 W4: 누락 key 디버그 로그 (각 key 당 1회만)
        if key not in _missing_keys_logged:
            _missing_keys_logged.add(key)
            try: _LOG.debug(f"[lang.tr] missing key: {key!r}")
            except Exception: pass
        return key
    text = s.get(_current_lang) or s.get("ko") or key
    if kwargs:
        try: return text.format(**kwargs)
        except Exception as e:
            try: _LOG.debug(f"[lang.tr] format failed for {key!r}: {e}")
            except Exception: pass
            return text
    return text


# ──────────────────────────────────────────────────────────
# v2.992.beta-5 hotfix6: material_db.json 값 번역
#
# material_db.json 의 일부 string 값 (categories / heat-treatment names /
# applications / notes / ref labels) 이 한국어로 작성되어 있음.
# DB 자체를 수정하지 않고, 렌더링 시 lookup table 로 동적 번역.
#
# Lookup 우선순위:
#   1) _DB_TRANSLATIONS 의 정확한 매치 (case-sensitive, full-string)
#   2) _DB_PATTERN_TRANSLATIONS 의 부분 매치 (substring → English alias)
#   3) 매치 없으면 원본 그대로 반환 (graceful fallback)
# ──────────────────────────────────────────────────────────

_DB_TRANSLATIONS = {
    # category descriptions (top-level material families)
    "오스테나이트 스테인리스강 (316L 계열)": "Austenitic stainless (316L family)",
    "Al-Sc-Zr 합금 (Scalmalloy 등)": "Al-Sc-Zr alloy (Scalmalloy etc.)",
    "Al-Si 주조합금 (AlSi10Mg, AlSi7Mg 등)": "Al-Si casting alloy (AlSi10Mg, AlSi7Mg etc.)",
    "Co-Cr 합금 (Co28Cr6Mo 등)": "Co-Cr alloy (Co28Cr6Mo etc.)",
    "Cu 합금 (CuCr1Zr, CuNi2SiCr 등)": "Cu alloy (CuCr1Zr, CuNi2SiCr etc.)",
    "석출경화 스테인리스강 (17-4PH/15-5PH)": "Precipitation-hardened stainless (17-4PH / 15-5PH)",
    "마레이징 강 (MS1/1.2709)": "Maraging steel (MS1 / 1.2709)",
    "공구강 (H13 등)": "Tool steel (H13 etc.)",

    # heat treatment names (high-level)
    "PH stainless 시효 등급 (°F)": "PH stainless aging grade (°F)",
    "HIP 후 어닐링": "HIP + Annealing",
    "용체화 + 시효 (Al/Ti)": "Solution + Aging (Al/Ti)",
    "용체화 + 시효 (Ni 합금)": "Solution + Aging (Ni alloy)",
    "응력 제거 어닐링 (SR)": "Stress-relief annealing (SR)",
    "AM 출력 직후": "As-built (just after AM)",
    "값+단위 (HRC/HV/HB)": "Value + unit (HRC/HV/HB)",
    "µm (마이크론)": "µm (microns)",
    "(텍스트)": "(text)",

    # applications (대다수 영어로 자연 번역)
    "고강도 항공/인공위성 구조 (APWORKS 특허)": "High-strength aerospace / satellite structures (APWORKS patent)",
    "고온 다이/사출 금형/압출 다이": "Hot work die / injection mold / extrusion die",
    "고전도성 + 고강도 부품": "High-conductivity + high-strength parts",
    "사출 금형/공구/항공 부품": "Injection mold / tooling / aerospace parts",
    "용접 전극/로켓 노즐 인서트": "Welding electrodes / rocket nozzle inserts",
    "의료/식품/해양/화학 장비": "Medical / food / marine / chemical equipment",
    "의료/화학 장비/해양": "Medical / chemical / marine equipment",
    "전기/열교환기/RF 안테나": "Electrical / heat exchangers / RF antennas",
    "주조 대체용 경량 부품": "Lightweight cast-replacement parts",
    "치과/의료 임플란트/가공 공구": "Dental / medical implants / machining tools",
    "터빈 디스크/우주 발사체/원자력 (~700°C)": "Turbine disks / launch vehicles / nuclear (~700°C)",
    "터빈 연소실/배기 (~1150°C)": "Turbine combustor / exhaust (~1150°C)",
    "항공/방산/터빈 부품": "Aerospace / defense / turbine parts",
    "항공/엔지니어링/산업용 부품": "Aerospace / engineering / industrial parts",
    "항공/의료 임플란트/모터스포츠": "Aerospace / medical implants / motorsports",
    "항공/자동차 경량 구조": "Aerospace / automotive lightweight structures",
    "해양/화학/배기 매니폴드": "Marine / chemical / exhaust manifolds",

    # notes (heat treatment descriptions)
    "AM 출력": "As-built",
    "1020°C 담금질 + 530°C 템퍼링 2회": "1020°C quench + 530°C tempering x2",
    "350°C × 2h (응력제거)": "350°C x 2h (stress-relief)",
    "AM 출력 (ASTM B162 / AMS5553)": "As-built (ASTM B162 / AMS5553)",
    "AM 출력 + 인공시효 325°C × 4h": "As-built + artificial aging 325°C x 4h",
    "AM 출력 — α' martensite": "As-built - α' martensite",
    "HIP 1160°C/4h/100 MPa + 용체화 + 시효": "HIP 1160°C/4h/100 MPa + Solution + Aging",
    "고경도 — 580°C 1회 템퍼링": "High hardness - 580°C single tempering",
    "고인성용 H1150": "H1150 for high toughness",
    "시효 552°C × 4h": "Aging 552°C x 4h",
    "시효 621°C × 4h (높은 인성)": "Aging 621°C x 4h (high toughness)",
    "어닐링 1175°C × 30min, water quench (AMS 5754)": "Annealing 1175°C x 30min, water quench (AMS 5754)",
    "어닐링 700°C × 1h": "Annealing 700°C x 1h",
    "어닐링 980°C × 1h (AMS 5666)": "Annealing 980°C x 1h (AMS 5666)",
    "용체화 + 시효": "Solution + Aging",
    "용체화 1040°C/30min + 시효 482°C/1h (AMS 5604)": "Solution 1040°C/30min + Aging 482°C/1h (AMS 5604)",
    "용체화 530°C/1h + 수냉 + 시효 160°C/12h": "Solution 530°C/1h + water-cool + Aging 160°C/12h",
    "용체화 815°C/1h + 시효 490°C/6h": "Solution 815°C/1h + Aging 490°C/6h",
    "용체화 980°C + 시효 460°C × 4h": "Solution 980°C + Aging 460°C x 4h",
    "용체화 980°C/1h + 시효 720°C/8h + 620°C/8h (AMS 5662)": "Solution 980°C/1h + Aging 720°C/8h + 620°C/8h (AMS 5662)",
    "응력제거 700°C × 2h": "Stress-relief 700°C x 2h",

    # ref_urls labels
    "Nikon SLM Steel 카탈로그": "Nikon SLM Steel catalog",
    "Nikon SLM Titanium 카탈로그": "Nikon SLM Titanium catalog",
}

# Partial-match fallback: substring → replacement.
# Useful for synthesized strings (e.g. dynamically built notes).
_DB_PATTERN_TRANSLATIONS = [
    ("AM 출력", "As-built"),
    ("용체화", "Solution"),
    ("시효", "Aging"),
    ("어닐링", "Annealing"),
    ("응력제거", "Stress-relief"),
    ("응력 제거", "Stress-relief"),
    ("담금질", "Quench"),
    ("템퍼링", "Tempering"),
    ("높은 인성", "high toughness"),
    ("고인성용", "for high toughness"),
    ("고경도", "High hardness"),
    ("수냉", "water-cool"),
    ("공냉", "air-cool"),
    ("열처리", "heat treatment"),
    ("카탈로그", "catalog"),
    ("제조사", "manufacturer"),
    ("장비", "machine"),
    ("(텍스트)", "(text)"),
    ("(마이크론)", "(microns)"),
    ("계열", "family"),
]


def tr_db(value, *, lang_override=None):
    """Translate a material_db.json string value for display.

    Args:
        value: original string (any language).
        lang_override: optional 'en' / 'ko'; defaults to current global language.

    Returns:
        Translated string if current language is 'en' AND a translation exists;
        otherwise the original string (graceful — works for unknown values).
    """
    if not isinstance(value, str) or not value:
        return value
    lang = lang_override or _current_lang
    if lang != "en":
        return value
    # 1) exact-match lookup
    if value in _DB_TRANSLATIONS:
        return _DB_TRANSLATIONS[value]
    # 2) substring-based replacement (preserves untranslated parts)
    out = value
    for ko, en in _DB_PATTERN_TRANSLATIONS:
        if ko in out:
            out = out.replace(ko, en)
    return out
