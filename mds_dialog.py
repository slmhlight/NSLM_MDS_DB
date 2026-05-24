"""ui.qt.mds_dialog - Qt material datasheet.

v2.916: 1) top material selector combo (in-dialog switch, main unaffected)
        2) surface roughness Ra display
        3) chart redesign: checkbox in vendor tree (default OFF),
           metric radio to chart right, [display data] row removed,
           font/padding fixes for no-clip rendering.
v2.915 hotfix3: [MDS] console log + QLabel constructor bug fix.
"""
from qt_helper import get_qt
import logging
_LOG = logging.getLogger("stl_analyzer.mds_dialog")
# v2.992.beta-5: i18n — 실패 시 한글 원문 fallback
try:
    from lang import tr as _tr, tr_db as _tr_db
except Exception:
    def _tr(_k): return None
    def _tr_db(v, **_): return v

def _T(key, fallback):
    v = _tr(key)
    return v if v else fallback


_open_windows = []


def _log(msg):
    try: _LOG.debug(f"[MDS] {msg}")
    except Exception: pass


def _safe_num(v, default=0.0):
    try:
        if v is None: return default
        if isinstance(v, (int, float)): return float(v)
        return float(str(v).strip().split()[0])
    except Exception:
        return default


def extract_manufacturers(props):
    """Derive supporting manufacturers from a material's vendor entries.

    Source of truth is `props['vendors']` — a dict whose values carry
    `manufacturer` strings (or fall back to the entry key prefix). Returns a
    de-duplicated, insertion-ordered list. No separate per-material vendors
    list needs to be stored anywhere.
    """
    vendors_dict = (props or {}).get("vendors") or {}
    if not isinstance(vendors_dict, dict):
        return []
    out = []
    seen = set()
    for vkey, vdata in vendors_dict.items():
        name = None
        if isinstance(vdata, dict):
            name = vdata.get("manufacturer")
        if not name and isinstance(vkey, str):
            # Fallback: parse the vendor-key prefix ("EOS [M290] @ ...")
            name = vkey.split("[", 1)[0].split("@", 1)[0].strip() or None
        if not name: continue
        if name in seen: continue
        seen.add(name)
        out.append(name)
    return out


def _fmt_num(v, spec=".0f", suffix=""):
    try:
        n = _safe_num(v, None)
        if n is None: return "-"
        return f"{n:{spec}}{suffix}"
    except Exception:
        return "-"


def _h_separator(Q):
    f = Q.QFrame()
    try: f.setFrameShape(Q.QFrame.HLine)
    except Exception:
        try: f.setFrameShape(Q.QFrame.Shape.HLine)
        except Exception: pass
    return f


class _VendorBarChart:
    """v2.916: vendor checkboxes are in external QTreeWidget column 0.
    v2.992.beta-5: vendors_new dict 지원."""
    def __init__(self, Q, C, G, parent, vp_data, tree_widget, vendors_new=None):
        self.Q = Q; self.C = C; self.G = G
        self.vp = vp_data or {}
        self.vendors_new = vendors_new or {}
        self.tree = tree_widget
        self.metric = "uts"
        self.host = Q.QWidget(parent)
        h = Q.QHBoxLayout(self.host); h.setContentsMargins(0, 0, 0, 0)
        self.canvas = _make_bar_canvas(Q, C, G, self)
        self.canvas.setMinimumHeight(260)
        h.addWidget(self.canvas, 1)
        metric_box = Q.QWidget()
        metric_box.setMaximumWidth(160)
        mv = Q.QVBoxLayout(metric_box); mv.setContentsMargins(8, 0, 0, 0)
        mlbl = Q.QLabel(_T("MD_CMP_ITEM", _T("MD_CMP_ITEM", "<b>비교 항목</b>")))
        mlbl.setStyleSheet("color:#1a3a6a; padding-bottom:4px;")
        mv.addWidget(mlbl)
        # v2.992.beta-5: YS Z 추가, 연신율 XY/Z 분리
        for short, mkey in [("UTS XY (MPa)", "uts"),
                             ("UTS Z (MPa)",  "uts_z"),
                             ("YS XY (MPa)", "ys"),
                             ("YS Z (MPa)", "ys_z"),
                             (_T("MD_RADIO_ELONG_XY", "연신율 XY (%)"), "elong_xy"),
                             (_T("MD_RADIO_ELONG_Z",  "연신율 Z (%)"),  "elong_z"),
                             (_T("MD_RADIO_HARD", "경도 (HV)"), "hardness_HV"),
                             (_T("MD_RADIO_RA", "표면조도 (μm)"), "surface_ra_hi")]:
            rb = Q.QRadioButton(short)
            if mkey == self.metric: rb.setChecked(True)
            rb.toggled.connect(
                lambda checked, k=mkey:
                self._on_metric(k) if checked else None)
            mv.addWidget(rb)
        mv.addStretch()
        h.addWidget(metric_box)
        try:
            tree_widget.itemChanged.connect(lambda *a: self._redraw())
        except Exception as e:
            _log(f"tree itemChanged connect: {e}")

    def _on_metric(self, m):
        self.metric = m
        self._redraw()

    def _redraw(self, *a):
        try: self.canvas.update()
        except Exception as e: _log(f"chart redraw err: {e}")

    def widget(self):
        return self.host

    def collect_data(self):
        data = []
        m = self.metric
        tw = self.tree
        try:
            n = tw.topLevelItemCount()
            for i in range(n):
                item = tw.topLevelItem(i)
                if not item: continue
                checked = (item.checkState(0) == self.C.Qt.Checked)
                if not checked: continue
                key = item.data(0, self.C.Qt.UserRole)
                if not key: continue
                vendor, layer, ht_key = key
                try:
                    # v2.992.beta-5: 새 vendors_new 구조 우선 (vendor key 가 dict 에 있으면)
                    if vendor in self.vendors_new:
                        vd = self.vendors_new[vendor]
                        # v2.992.beta-5: surface_ra_hi 가 None 으로 매핑돼 비교 작동 안 하던 버그 + ys_z 추가
                        mkey_map = {
                            "uts":           "uts_xy_MPa",
                            "uts_z":         "uts_z_MPa",
                            "ys":            "yield_MPa",
                            "ys_z":          "yield_z_MPa",
                            "elong_xy":      "elongation_xy_pct",
                            "elong_z":       "elongation_z_pct",
                            "hardness_HV":   "hardness_HV",
                            "surface_ra_hi": "surface_ra_hi",
                        }
                        vd_k = mkey_map.get(m)
                        v = vd.get(vd_k) if vd_k else None
                        if v is None or v == 0: continue
                        # v2.992.beta-5: manufacturer 가 None 으로 명시된 vendor 도 안전
                        manuf = (vd.get("manufacturer") or "?")[:12]
                        machine = vd.get("machine", "") or ""
                        post = vd.get("post_treatment", "") or ""
                        lt = vd.get("layer_thickness_um", "?")
                        lbl2 = f"{machine[:10]} {lt}μm".strip()
                        parts = [manuf, lbl2]
                        if post and post.lower() != "as-built":
                            parts.append(f"({post[:8]})")
                        label = "\n".join(parts)
                        data.append((label, _safe_num(v, 0)))
                        continue
                    # legacy vendor_properties 경로
                    if layer == "_":
                        vals = self.vp[vendor][ht_key]
                        label = f"{vendor[:10]}\n{ht_key}"
                    else:
                        vals = self.vp[vendor][layer][ht_key]
                        label = f"{vendor[:8]}\n{layer[:8]}\n{ht_key}"
                    v = vals.get(m)
                    if v is None or v == 0: continue
                    data.append((label, _safe_num(v, 0)))
                except Exception as ex:
                    _log(f"chart collect row err: {ex}")
        except Exception as e:
            _log(f"chart collect err: {e}")
        return data


def _make_bar_canvas(Q, C, G, parent_chart):
    class _BarCanvas(Q.QWidget):
        def __init__(self, pc):
            super().__init__()
            self._pc = pc

        def paintEvent(self, ev):
            try:
                p = G.QPainter(self)
                p.setRenderHint(G.QPainter.Antialiasing)
                W = self.width(); H = self.height()
                pad_l = 50; pad_r = 24; pad_t = 30; pad_b = 70
                p.fillRect(0, 0, W, H, G.QColor("#fafbfc"))
                data = self._pc.collect_data()
                if not data:
                    p.setPen(G.QColor("#888"))
                    f = p.font(); f.setPointSize(10); p.setFont(f)
                    p.drawText(self.rect(), C.Qt.AlignCenter,
                                _T("MD_NO_CHECKED", "체크된 데이터가 없습니다") + "\n"
                                + _T("MD_TREE_HINT", "(좌측 트리에서 체크하세요)"))
                    p.end(); return
                metric = self._pc.metric
                unit_map = {"uts": "MPa", "uts_z": "MPa",
                             "ys": "MPa", "ys_z": "MPa",
                             "elong_xy": "%", "elong_z": "%",
                             "hardness_HV": "HV",
                             "surface_ra_hi": "μm"}
                max_v = max(d[1] for d in data) * 1.18
                if max_v <= 0: max_v = 1.0
                n = len(data)
                # v2.992.beta-5: n=0 가드 (data 비어있을 시 div-by-zero 방지)
                if n <= 0: return
                avail_w = W - pad_l - pad_r
                bar_w = avail_w / n * 0.72
                gap = avail_w / n * 0.28
                colors = ["#3a78d8", "#cc6622", "#1a8a3a", "#a82a82",
                           "#d8a800", "#6a4ac8", "#aa3030", "#3a8a8a",
                           "#5a9ad8", "#dc7632", "#2a9a4a", "#b83a92"]
                f = p.font(); f.setPointSize(9); p.setFont(f)
                p.setPen(G.QColor("#444"))
                p.drawText(4, pad_t - 8, f"{int(max_v)}")
                p.drawText(4, H - pad_b + 14, "0")
                p.drawText(4, (pad_t + H - pad_b) // 2,
                            f"({unit_map.get(metric, '')})")
                p.setPen(G.QPen(G.QColor("#999"), 1))
                p.drawLine(pad_l, pad_t, pad_l, H - pad_b)
                p.drawLine(pad_l, H - pad_b, W - pad_r, H - pad_b)
                p.setPen(G.QPen(G.QColor("#e0e0e0"), 1, C.Qt.DashLine))
                mid_y = (pad_t + H - pad_b) // 2
                p.drawLine(pad_l, mid_y, W - pad_r, mid_y)
                p.setPen(G.QColor("#666"))
                p.drawText(4, mid_y + 4, f"{int(max_v/2)}")
                for i, (lbl, val) in enumerate(data):
                    x = pad_l + i * (bar_w + gap) + gap/2
                    bar_h = (val / max_v) * (H - pad_t - pad_b)
                    y2 = H - pad_b; y1 = y2 - bar_h
                    col = G.QColor(colors[i % len(colors)])
                    p.setPen(G.QPen(G.QColor("#333"), 1))
                    p.setBrush(col)
                    p.drawRect(int(x), int(y1), int(bar_w), int(bar_h))
                    fb = p.font(); fb.setPointSize(9); fb.setBold(True)
                    p.setFont(fb)
                    p.setPen(G.QColor("#000"))
                    p.drawText(int(x), int(y1 - 20), int(bar_w), 18,
                                C.Qt.AlignCenter,
                                f"{val:.0f}" if val >= 10 else f"{val:.1f}")
                    fl = p.font(); fl.setPointSize(8); fl.setBold(False)
                    p.setFont(fl)
                    p.setPen(G.QColor("#222"))
                    p.drawText(int(x - gap/4), int(y2 + 4),
                                int(bar_w + gap/2), int(pad_b - 8),
                                C.Qt.AlignHCenter | C.Qt.AlignTop, lbl)
                p.end()
            except Exception as exc:
                _log(f"BarCanvas paintEvent err: {exc}")
                try: p.end()
                except Exception: pass
    return _BarCanvas(parent_chart)


def open_mds_qt(material_name, properties, vendors=None, mds_urls=None,
                 default_vendors_4=None, material_db=None):
    """Open the material data-sheet dialog.

    Args:
        material_name: initial material
        properties: initial props
        vendors: deprecated — derived from properties['vendors'] entries
                 via extract_manufacturers(). Accepted only for compat.
        mds_urls: initial ref_urls
        default_vendors_4: DB _default_4
        material_db: full DB (None disables combo)
    Returns: True/False
    """
    _log(f"=== open_mds_qt START === material={material_name!r}, "
          f"has material_db: {material_db is not None}")

    qt = get_qt()
    if qt is None:
        _log("get_qt() returned None")
        return False
    Q = qt["QtWidgets"]; C = qt["QtCore"]; G = qt["QtGui"]
    app = qt.get("app")

    try:
        win = Q.QWidget()
        win.setWindowTitle(f"MDS - {material_name}")
        # Force a light theme inside this dialog regardless of the OS-level
        # dark-mode palette. Without this, on a dark-mode machine Qt picks a
        # light-text default that becomes invisible against our explicit
        # `#fafbfc` widget backgrounds.
        # We use BOTH a palette override (inherited by children even when they
        # have their own setStyleSheet) AND a stylesheet for visual polish.
        try:
            _pal = win.palette()
            _light_pairs = [
                ("Window",         "#ffffff"),
                ("WindowText",     "#222222"),
                ("Base",           "#ffffff"),
                ("AlternateBase",  "#f3f6fa"),
                ("Text",           "#222222"),
                ("Button",         "#f0f0f0"),
                ("ButtonText",     "#222222"),
                ("ToolTipBase",    "#ffffe1"),
                ("ToolTipText",    "#222222"),
                ("Highlight",      "#cfe2ff"),
                ("HighlightedText", "#000000"),
                ("PlaceholderText", "#888888"),
            ]
            for role_name, hex_col in _light_pairs:
                role = getattr(G.QPalette, role_name, None)
                if role is not None:
                    _pal.setColor(role, G.QColor(hex_col))
            win.setPalette(_pal)
        except Exception as e:
            _log(f"palette set fail (dark-mode override): {e}")

        win.setStyleSheet("""
            QWidget { background-color: #ffffff; color: #222222; }
            QGroupBox {
                background-color: #ffffff; color: #1a3a6a;
                border: 1px solid #d0d4da; border-radius: 4px;
                margin-top: 10px; padding-top: 4px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 8px; padding: 0 4px;
                color: #1a3a6a;
            }
            QLabel, QCheckBox, QRadioButton { color: #222222; }
            QTextEdit, QPlainTextEdit, QLineEdit {
                background-color: #fafbfc; color: #222222;
                selection-background-color: #cfe2ff;
                selection-color: #000000;
            }
            QTreeWidget, QTreeView, QListView, QTableWidget, QTableView {
                background-color: #ffffff; color: #222222;
                alternate-background-color: #f3f6fa;
                selection-background-color: #cfe2ff;
                selection-color: #000000;
                gridline-color: #d0d4da;
            }
            QHeaderView::section {
                background-color: #eef1f5; color: #1a3a6a;
                border: 1px solid #d0d4da; padding: 4px;
            }
            QTabWidget::pane { background-color: #ffffff; border: 1px solid #d0d4da; }
            QTabBar::tab {
                background-color: #ececec; color: #333333;
                padding: 6px 12px; border: 1px solid #d0d4da;
                border-bottom: none;
            }
            QTabBar::tab:selected { background-color: #ffffff; color: #1a3a6a; }
            QPushButton {
                background-color: #f0f0f0; color: #222222;
                border: 1px solid #c0c4ca; border-radius: 3px;
                padding: 4px 10px;
            }
            QPushButton:hover { background-color: #e6e6e6; }
            QPushButton:pressed { background-color: #d8d8d8; }
            QComboBox {
                background-color: #ffffff; color: #222222;
                border: 1px solid #c0c4ca; padding: 2px 4px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff; color: #222222;
                selection-background-color: #cfe2ff;
            }
            QToolButton { color: #1a3a6a; }
            QToolTip {
                background-color: #ffffe1; color: #222222;
                border: 1px solid #c0c4ca;
            }
        """)
        try:
            screen = app.primaryScreen().size()
            mw = min(1500, max(1200, int(screen.width() * 0.78)))
            mh = min(950, max(760, int(screen.height() * 0.82)))
            win.resize(mw, mh)
        except Exception:
            win.resize(1300, 820)

        outer = Q.QVBoxLayout(win)
        outer.setContentsMargins(8, 8, 8, 8)

        # ---- Top: category filter + material selector ----
        top = Q.QHBoxLayout()

        # Category dropdown (Nikon-aligned top-level grouping).
        top.addWidget(Q.QLabel(_T("MD_CAT_FILTER", "<b>Category:</b>")))
        cat_combo = Q.QComboBox()
        cat_combo.setMinimumWidth(140)
        ALL_LABEL = _T("MD_CAT_ALL", "All")
        cat_combo.addItem(ALL_LABEL)
        # Category order comes from the DB so it stays in sync with the
        # categorization tool. Fall back to Nikon's literal slug list.
        _cat_order = (material_db.get("_category_top_order") if material_db
                      else None) or [
            "Aluminium", "Cobalt", "Copper", "Nickel",
            "Steel", "Titanium", "Niobium", "Other",
        ]
        for c in _cat_order: cat_combo.addItem(c)
        cat_combo.setToolTip(
            "Filter the material list by Nikon-style top-level category.\n"
            "Categories follow https://nikon-slm-solutions.com/materials/\n"
            "(refractory metals not listed by Nikon → 'Other').")
        top.addWidget(cat_combo)
        top.addSpacing(16)

        # Material dropdown — populated initially with everything.
        top.addWidget(Q.QLabel(_T("MD_MAT", _T("MD_MAT", "<b>Material:</b>"))))
        mat_combo = Q.QComboBox()
        mat_combo.setMinimumWidth(280)

        # The full material → category_top map drives filtering on every
        # category-combo change. Building it once here is cheap (<60 items).
        all_mats_in_order = (list((material_db.get("materials", {}) or {}).keys())
                             if material_db else [material_name])
        mat_to_cat = {}
        if material_db:
            for m in all_mats_in_order:
                mat_to_cat[m] = (material_db["materials"][m].get("category_top")
                                  or "Other")

        def _populate_materials(selected_cat: str):
            """Refill mat_combo based on the active category."""
            try: mat_combo.blockSignals(True)
            except Exception: pass
            mat_combo.clear()
            if not material_db:
                mat_combo.addItem(material_name)
                mat_combo.setEnabled(False)
                try: mat_combo.blockSignals(False)
                except Exception: pass
                return
            shown = (all_mats_in_order if selected_cat == ALL_LABEL
                     else [m for m in all_mats_in_order
                           if mat_to_cat.get(m) == selected_cat])
            for m in shown: mat_combo.addItem(m)
            # Keep the current material selected if it survives the filter
            try:
                idx = shown.index(material_name)
                mat_combo.setCurrentIndex(idx)
            except ValueError:
                pass
            try: mat_combo.blockSignals(False)
            except Exception: pass

        _populate_materials(ALL_LABEL)
        top.addWidget(mat_combo)
        top.addSpacing(20)
        cat_lbl = Q.QLabel("")
        cat_lbl.setStyleSheet("color: #666; font-style: italic;")
        top.addWidget(cat_lbl)
        top.addStretch()
        outer.addLayout(top)
        outer.addWidget(_h_separator(Q))

        # Category-combo signal is wired AFTER _on_material_changed is defined
        # below, so that filtering the list also triggers a body rebuild for
        # the first material in the newly-filtered set.

        body_host = Q.QWidget()
        body_layout = Q.QVBoxLayout(body_host)
        body_layout.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(body_host, 1)

        def _build_body(mat_name, props, urls):
            while body_layout.count():
                item = body_layout.takeAt(0)
                w = item.widget()
                if w is not None: w.deleteLater()
            cat_lbl.setText(_T("MD_CATEGORY", "카테고리: {cat}").format(
                cat=_tr_db(props.get('category', '-'))))

            splitter = Q.QSplitter(C.Qt.Horizontal)
            body_layout.addWidget(splitter, 1)

            # Left col
            left = Q.QWidget(); l_lay = Q.QVBoxLayout(left)
            l_lay.setContentsMargins(0, 0, 4, 0)

            basic_box = Q.QGroupBox(_T("MD_BASIC_PHYS", _T("MD_BASIC_PHYS", "기본 물리 / 열적 (열처리 무관)")))
            bv = Q.QVBoxLayout(basic_box)
            basic_text = Q.QTextEdit(); basic_text.setReadOnly(True)
            try: basic_text.setFont(G.QFont("Consolas", 10))
            except Exception: pass
            basic_text.setMaximumHeight(190)
            basic_text.setStyleSheet("background:#fafbfc;")
            # v2.992.beta-5 hotfix5: label i18n via _T
            def _lbl(key, fallback, w=14):
                t = _T(key, fallback)
                return t + " " * max(2, w - len(t))
            basic_lines = [
                f"  {_lbl('MD_BASIC_DENSITY', '밀도')}: {_fmt_num(props.get('density'), '.3f'):>10} g/cm3",
                f"  {_lbl('MD_BASIC_MELT',    '녹는점')}: {_fmt_num(props.get('melt'), '.0f'):>10} C",
                f"  {_lbl('MD_BASIC_MAG',     '자성')}: {_tr_db(props.get('magnetic','-'))}",
                f"  {_lbl('MD_BASIC_YOUNGS',  '영률 (E)')}: {_fmt_num(props.get('E'), '.0f'):>10} GPa",
                f"  {_lbl('MD_BASIC_POISSON', '포아송 비')}: {_fmt_num(props.get('poisson'), '.3f'):>10}",
                f"  {_lbl('MD_BASIC_THERMK', '열전도율')}: {_fmt_num(props.get('thermal_k'), '.1f'):>10} W/m K",
                f"  {_lbl('MD_BASIC_CP',     '비열 (Cp)')}: {_fmt_num(props.get('cp'), '.0f'):>10} J/kg K",
                f"  {_lbl('MD_BASIC_CTE',    '열팽창 (CTE)')}: {_fmt_num(props.get('cte'), '.1f'):>10} 10-6/K",
            ]
            basic_text.setPlainText("\n".join(basic_lines))
            bv.addWidget(basic_text)
            l_lay.addWidget(basic_box)

            ht_lbl = Q.QLabel(_T("MD_HEAT_TREAT", _T("MD_HEAT_TREAT", "◆ 열처리 별 기계적 물성 + 표면조도")))
            ht_lbl.setStyleSheet(
                "font-weight: bold; color: #1a3a6a; padding-top: 4px;")
            l_lay.addWidget(ht_lbl)
            nb = Q.QTabWidget()
            ht_dict = props.get("heat_treatments", {}) or {}
            if ht_dict:
                for ht_key, ht_data in ht_dict.items():
                    if not isinstance(ht_data, dict): continue
                    tab = Q.QWidget(); tv = Q.QVBoxLayout(tab)
                    txt = Q.QTextEdit(); txt.setReadOnly(True)
                    try: txt.setFont(G.QFont("Consolas", 10))
                    except Exception: pass
                    txt.setStyleSheet("background:#fafbfc;")
                    h_lines = []
                    if ht_data.get("hardness_HV"):
                        h_lines.append(f"{ht_data['hardness_HV']} HV")
                    if ht_data.get("hardness_HRC") not in (None, 0, ""):
                        h_lines.append(f"{ht_data['hardness_HRC']} HRC")
                    if ht_data.get("hardness_HB"):
                        h_lines.append(f"{ht_data['hardness_HB']} HB")
                    hardness_str = " / ".join(h_lines) or "-"
                    ra = ht_data.get("surface_ra_um") or "-"
                    # v2.992.beta-5 hotfix5: label i18n
                    def _htlbl(key, fb, w=22):
                        t = _T(key, fb)
                        return t + " " * max(2, w - len(t))
                    content = [
                        f"{_htlbl('MD_HT_UTS',   '인장강도 (UTS)')}: {_fmt_num(ht_data.get('uts'),'.0f'):>8} MPa",
                        f"{_htlbl('MD_HT_YS',    '항복강도 (YS, 0.2%)')}: {_fmt_num(ht_data.get('ys'),'.0f'):>8} MPa",
                        f"{_htlbl('MD_HT_ELONG', '연신율 (Elongation)')}: {_fmt_num(ht_data.get('elong'),'.1f'):>8} %",
                        f"{_htlbl('MD_HT_HARD',  '경도')}: {hardness_str}",
                        f"{_htlbl('MD_HT_RA',    '표면조도 Ra (μm)')}: {ra}  (SLM as-built, side wall)",
                        "",
                        _T("MD_HT_STD", "[열처리 표준 / 설명]"),
                        f"  {_tr_db(ht_data.get('notes') or '-')}",
                    ]
                    txt.setPlainText("\n".join(content))
                    tv.addWidget(txt)
                    # ht_key (예: "as_built", "annealed", "HT_HIP" 등) 의 lookup
                    #  + 정의된 ko-tag 가 있으면 EN 변환. underscore/hyphen 기반 키는
                    #  변환 dict 에 없으면 그대로 (graceful).
                    nb.addTab(tab, _tr_db(ht_key))
            else:
                ph = Q.QLabel(_T("MD_NO_HEAT", _T("MD_NO_HEAT", "(열처리 데이터 없음)")))
                ph.setAlignment(C.Qt.AlignCenter)
                nb.addTab(ph, _T("MD_NO_DATA_TAB", "데이터 없음"))

            # v2.992.beta-5: 새 vendors nested 구조 (CSV 통합 데이터)
            vendors_new = props.get("vendors", {}) or {}
            vp = props.get("vendor_properties", {}) or {}
            if vendors_new or vp:
                try:
                    vp_tab = Q.QWidget(); vp_v = Q.QVBoxLayout(vp_tab)
                    tree = Q.QTreeWidget()
                    # 12 columns: TDS shortcut as the rightmost column
                    tree.setColumnCount(12)
                    tree.setHeaderLabels(
                        [_T("MD_COL_MFG", "제조사"),
                         _T("MD_COL_MACHINE", "장비"),
                         _T("MD_COL_POST", "후처리"), "Layer\nμm",
                         "YS XY\nMPa", "YS Z\nMPa",
                         "UTS XY\nMPa", "UTS Z\nMPa",
                         _T("MD_COL_ELONG", "연신율\nXY/Z %"),
                         _T("MD_COL_HARD", "경도\nHV"),
                         "Ra\nμm",
                         _T("MD_COL_TDS", "TDS")])
                    tree.setRootIsDecorated(False)
                    tree.setAlternatingRowColors(True)
                    # v2.992.beta-5: 8줄 보이도록 확장 (새 vendor 수 대폭 증가)
                    try:
                        rh = tree.sizeHintForRow(0)
                        if rh <= 0: rh = 28  # 멀티라인 헤더 고려
                        tree.setMaximumHeight(rh * 8 + 50)
                        tree.setMinimumHeight(rh * 5 + 50)
                    except Exception:
                        tree.setMaximumHeight(260)
                        tree.setMinimumHeight(180)
                    try:
                        hf = tree.header().font()
                        hf.setBold(True)
                        tree.header().setFont(hf)
                    except Exception: pass
                    def _fmt(x):
                        if x is None or x == "" or x == "-": return "-"
                        try:
                            xf = float(x)
                            if xf.is_integer(): return str(int(xf))
                            return f"{xf:.1f}"
                        except Exception:
                            return str(x)
                    def _fmt_ra(vd):
                        """v2.992.beta-5: 표면조도 (Ra) lo~hi 범위 표시."""
                        lo = vd.get("surface_ra_lo")
                        hi = vd.get("surface_ra_hi")
                        if lo is None and hi is None: return "-"
                        if lo is None: return _fmt(hi)
                        if hi is None: return _fmt(lo)
                        if lo == hi: return _fmt(lo)
                        return f"{_fmt(lo)}~{_fmt(hi)}"

                    def _fmt_elong(vd):
                        """Show XY/Z elongation as 'xy / z' (or single value, or '-')."""
                        xy = vd.get("elongation_xy_pct")
                        z  = vd.get("elongation_z_pct")
                        if xy is None and z is None:
                            # Legacy: fall back to single field
                            return _fmt(vd.get("elongation_pct"))
                        if xy is not None and z is not None and xy != z:
                            return f"{_fmt(xy)} / {_fmt(z)}"
                        return _fmt(xy if xy is not None else z)
                    # v2.992.beta-5: 새 vendors dict — YS Z + 표면조도 추가 (11 columns)
                    for vendor_key, vdata in vendors_new.items():
                        manuf = vdata.get("manufacturer", vendor_key)
                        machine = vdata.get("machine", "-") or "-"
                        post = vdata.get("post_treatment", "-") or "-"
                        # TDS column: small "📄" if a link exists, else "-".
                        # Click handler below opens the URL in the browser.
                        tds_url = vdata.get("tds_link")
                        tds_cell = "📄" if tds_url else "-"
                        item = Q.QTreeWidgetItem([
                            str(manuf),
                            str(machine),
                            str(post),
                            _fmt(vdata.get("layer_thickness_um")),
                            _fmt(vdata.get("yield_MPa")),
                            _fmt(vdata.get("yield_z_MPa")),
                            _fmt(vdata.get("uts_xy_MPa")),
                            _fmt(vdata.get("uts_z_MPa")),
                            _fmt_elong(vdata),
                            _fmt(vdata.get("hardness_HV")),
                            _fmt_ra(vdata),
                            tds_cell,
                        ])
                        item.setFlags(item.flags() | C.Qt.ItemIsUserCheckable)
                        item.setCheckState(0, C.Qt.Unchecked)
                        item.setData(0, C.Qt.UserRole, (vendor_key, "_", post))
                        # Stash the URL on the item so the click handler can read it
                        if tds_url:
                            item.setData(11, C.Qt.UserRole, tds_url)
                            try:
                                item.setForeground(11, G.QBrush(G.QColor("#0066cc")))
                            except Exception: pass
                        # 툴팁: TDS link, notes
                        _tip_parts = []
                        if tds_url:
                            _tip_parts.append(f"TDS: {tds_url}")
                            item.setToolTip(11,
                                f"Click — open TDS\n{tds_url}")
                        if vdata.get("notes"):
                            _tip_parts.append(f"Notes: {_tr_db(vdata['notes'])}")
                        if vdata.get("test_standard"):
                            _tip_parts.append(f"Std: {vdata['test_standard']}")
                        if _tip_parts:
                            item.setToolTip(0, "\n".join(_tip_parts))
                        tree.addTopLevelItem(item)
                    # v2.992.beta-5: legacy vp 구조도 병행 표시 (있으면)
                    for vendor, vd in vp.items():
                        first_val = next(iter(vd.values()), {})
                        is_layered = (isinstance(first_val, dict)
                            and any(isinstance(v, dict) for v in first_val.values()))
                        if is_layered:
                            for layer, ht_data in vd.items():
                                for ht_key, vals in ht_data.items():
                                    label = f"{vendor} / {layer}"
                                    item = Q.QTreeWidgetItem([
                                        label, "-", ht_key, "-",
                                        _fmt(vals.get("ys")),
                                        "-",
                                        _fmt(vals.get("uts")),
                                        "-",
                                        _fmt(vals.get("elong")),
                                        _fmt(vals.get("hardness_HV")),
                                        "-",
                                        "-",  # TDS: legacy entries have no link
                                    ])
                                    item.setFlags(item.flags() | C.Qt.ItemIsUserCheckable)
                                    item.setCheckState(0, C.Qt.Unchecked)
                                    item.setData(0, C.Qt.UserRole,
                                                  (vendor, layer, ht_key))
                                    tree.addTopLevelItem(item)
                        else:
                            for ht_key, vals in vd.items():
                                item = Q.QTreeWidgetItem([
                                    vendor, "-", ht_key, "-",
                                    _fmt(vals.get("ys")),
                                    "-",
                                    _fmt(vals.get("uts")),
                                    "-",
                                    _fmt(vals.get("elong")),
                                    _fmt(vals.get("hardness_HV")),
                                    "-",
                                    "-",  # TDS: legacy entries have no link
                                ])
                                item.setFlags(item.flags() | C.Qt.ItemIsUserCheckable)
                                item.setCheckState(0, C.Qt.Unchecked)
                                item.setData(0, C.Qt.UserRole, (vendor, "_", ht_key))
                                tree.addTopLevelItem(item)
                    # 컬럼 폭 — 퍼센트 기준 (tree 너비에 비례 자동 분배).
                    # 12 columns: 제조사 13, 장비 13, 후처리 9, Layer 6,
                    # YS XY 7, YS Z 7, UTS XY 7, UTS Z 7,
                    # 연신율 7, 경도 7, Ra 11, TDS 6  = 100
                    _col_pcts = [13, 13, 9, 6, 7, 7, 7, 7, 7, 7, 11, 6]
                    def _apply_pct_widths():
                        try:
                            tw = tree.viewport().width()
                            if tw < 200: tw = 1100  # 초기 표시 전 fallback
                            for ci, pp in enumerate(_col_pcts):
                                w = max(45, int(tw * pp / 100))
                                tree.setColumnWidth(ci, w)
                        except Exception: pass
                    # 초기 1회 + 표시 후 1회 (viewport 너비 확정 후)
                    _apply_pct_widths()
                    try:
                        C.QTimer.singleShot(0, _apply_pct_widths)
                    except Exception: pass
                    # 리사이즈 시에도 비율 유지
                    try:
                        _orig_resize = tree.resizeEvent
                        def _on_tree_resize(ev):
                            _orig_resize(ev)
                            _apply_pct_widths()
                        tree.resizeEvent = _on_tree_resize
                    except Exception: pass
                    try:
                        tree.header().setStretchLastSection(False)
                        tree.header().setDefaultAlignment(C.Qt.AlignCenter)
                        # v2.992.beta-5: 컬럼 클릭 정렬 활성화
                        tree.setSortingEnabled(True)
                    except Exception: pass
                    # v2.992.beta-5: Nikon SLM Solutions → Major 4 (EOS/Renishaw/3D Systems/SLM Solutions) → 나머지
                    _MAJOR_ORDER = {
                        "Nikon SLM Solutions": 0,
                        "EOS": 1,
                        "Renishaw": 2,
                        "3D Systems": 3,
                        "SLM Solutions": 4,
                    }
                    _items = []
                    while tree.topLevelItemCount() > 0:
                        _items.append(tree.takeTopLevelItem(0))
                    def _sort_key(it):
                        manuf = it.text(0)
                        prio = _MAJOR_ORDER.get(manuf, 99)
                        return (prio, manuf, it.text(1), it.text(2))
                    _items.sort(key=_sort_key)
                    for _it in _items: tree.addTopLevelItem(_it)

                    # TDS column (index 11): single-click opens the URL in
                    # the default browser. Falls back to copying to the
                    # clipboard if open fails (some kiosk-style setups).
                    def _on_tree_clicked(it, col):
                        if col != 11: return
                        url = it.data(11, C.Qt.UserRole)
                        if not url: return
                        try:
                            import webbrowser
                            webbrowser.open(url)
                            _log(f"TDS opened: {url}")
                        except Exception as e:
                            _log(f"TDS open failed: {e}")
                            try:
                                app.clipboard().setText(url)
                                Q.QMessageBox.information(
                                    win, "TDS URL copied",
                                    "Browser could not open; URL copied to clipboard.\n\n" + url)
                            except Exception: pass
                    try:
                        tree.itemClicked.connect(_on_tree_clicked)
                    except Exception as e:
                        _log(f"tree itemClicked connect: {e}")

                    vp_v.addWidget(tree)
                    chart = _VendorBarChart(Q, C, G, vp_tab, vp, tree, vendors_new=vendors_new)
                    vp_v.addWidget(chart.widget(), 1)

                    # Report-generation button — gathers all checked rows
                    # into a standalone HTML report (inline SVG charts).
                    rpt_row = Q.QHBoxLayout()
                    rpt_row.addStretch()
                    btn_report = Q.QPushButton(
                        _T("MD_REPORT_BTN", "📊 선택 entry로 보고서 생성"))
                    btn_report.setToolTip(
                        "Generate a standalone HTML report with tables\n"
                        "and charts for every checked vendor entry.")
                    btn_report.setMinimumWidth(220)

                    def _on_report():
                        # Collect checked rows from the vendor tree
                        selected = []
                        try:
                            n = tree.topLevelItemCount()
                            for i in range(n):
                                it = tree.topLevelItem(i)
                                if not it: continue
                                if it.checkState(0) != C.Qt.Checked: continue
                                key = it.data(0, C.Qt.UserRole)
                                if not key: continue
                                vendor_key = key[0]
                                vd = vendors_new.get(vendor_key)
                                if isinstance(vd, dict):
                                    selected.append((vendor_key, vd))
                        except Exception as e:
                            _log(f"report collect err: {e}")

                        if not selected:
                            Q.QMessageBox.information(
                                win, _T("MD_REPORT_NONE", "선택된 entry 없음"),
                                _T("MD_REPORT_NONE_MSG",
                                   "보고서를 만들 entry를 먼저 좌측 트리에서 체크하세요."))
                            return

                        # Suggest a sensible default filename
                        safe_mat = "".join(
                            ch if ch.isalnum() or ch in " -_" else "_"
                            for ch in mat_name)
                        ts = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
                        default_fn = f"MDS_{safe_mat}_{ts}.html"

                        fn, _flt = Q.QFileDialog.getSaveFileName(
                            win,
                            _T("MD_REPORT_SAVE_TITLE", "Save report as"),
                            default_fn,
                            "HTML (*.html);;All files (*)")
                        if not fn: return
                        if not fn.lower().endswith(".html"):
                            fn = fn + ".html"

                        try:
                            from report_generator import build_report_html
                            html = build_report_html(mat_name, props, selected)
                            with open(fn, "w", encoding="utf-8") as f:
                                f.write(html)
                            _log(f"report written: {fn}  ({len(html)} chars, "
                                 f"{len(selected)} entries)")
                        except Exception as ee:
                            import traceback as _tb
                            _log(f"report build fail: {ee}\n{_tb.format_exc()}")
                            Q.QMessageBox.critical(
                                win, "Report generation failed",
                                f"{type(ee).__name__}: {ee}")
                            return

                        # Open in default browser (best-effort)
                        try:
                            import webbrowser, pathlib
                            webbrowser.open(pathlib.Path(fn).as_uri())
                        except Exception as ee:
                            _log(f"report open fail: {ee}")

                        Q.QMessageBox.information(
                            win, "Report generated",
                            f"Generated report from {len(selected)} entries.\n\n{fn}")

                    btn_report.clicked.connect(_on_report)
                    rpt_row.addWidget(btn_report)
                    rpt_row.addStretch()
                    vp_v.addLayout(rpt_row)

                    nb.addTab(vp_tab, _T("MD_TAB_VENDOR", "🏭 제조사별 차이"))
                except Exception as e:
                    import traceback as _tb
                    _log(f"vendor tab build FAIL: {e}\n{_tb.format_exc()}")

            l_lay.addWidget(nb, 1)
            splitter.addWidget(left)

            # Right col
            right = Q.QWidget(); r_lay = Q.QVBoxLayout(right)
            r_lay.setContentsMargins(4, 0, 0, 0)
            vend_box = Q.QGroupBox(_T("MD_VENDORS_OFFICIAL", _T("MD_VENDORS_OFFICIAL", "공식 지원 회사 (체크리스트)")))
            vv = Q.QVBoxLayout(vend_box)
            d4 = default_vendors_4 or [
                "Nikon SLM Solutions", "EOS", "Renishaw", "TRUMPF"]
            # Derive supporters straight from vendor entries (no separate list)
            derived = extract_manufacturers(props)
            for v_name in d4:
                checked = v_name in derived
                mark = "☑" if checked else "☐"
                lbl = Q.QLabel(f"{mark}  {v_name}")
                if checked:
                    lbl.setStyleSheet(
                        "color: #1a6a3a; font-weight: bold; padding: 1px;")
                else:
                    lbl.setStyleSheet("color: #888; padding: 1px;")
                vv.addWidget(lbl)
            extras = [v for v in derived if v not in d4]
            if extras:
                vv.addWidget(_h_separator(Q))
                ext_lbl = Q.QLabel(_T("MD_VENDORS_EXTRA", _T("MD_VENDORS_EXTRA", "<b>추가 지원사:</b>")))
                ext_lbl.setStyleSheet("color: #1a3a6a;")
                vv.addWidget(ext_lbl)
                for v_name in extras:
                    ext_item = Q.QLabel(f"  ☑  {v_name}")
                    ext_item.setStyleSheet("color: #1a6a3a;")
                    vv.addWidget(ext_item)
            r_lay.addWidget(vend_box)

            comp_box = Q.QGroupBox(_T("MD_COMP", _T("MD_COMP", "화학 조성 (% by weight)")))
            cv = Q.QVBoxLayout(comp_box)
            comp_table = Q.QTableWidget()
            comp_table.setColumnCount(2)
            comp_table.setHorizontalHeaderLabels(["Element", "wt %"])
            comp = props.get("composition", []) or []
            comp_table.setRowCount(len(comp))
            for i, c in enumerate(comp):
                try:
                    if isinstance(c, dict):
                        el = c.get("element", "?"); pct = c.get("pct", "-")
                    elif isinstance(c, (list, tuple)) and len(c) >= 2:
                        el, pct = c[0], c[1]
                    else:
                        el = str(c); pct = "-"
                    it_el = Q.QTableWidgetItem(str(el))
                    try: it_el.setTextAlignment(C.Qt.AlignCenter)
                    except Exception: pass
                    comp_table.setItem(i, 0, it_el)
                    comp_table.setItem(i, 1, Q.QTableWidgetItem(str(pct)))
                except Exception as e:
                    _log(f"comp row {i} fail: {e}")
            try:
                comp_table.horizontalHeader().setStretchLastSection(True)
                comp_table.verticalHeader().setVisible(False)
            except Exception: pass
            cv.addWidget(comp_table)
            r_lay.addWidget(comp_box, 1)

            app_box = Q.QGroupBox(_T("MD_APP", "응용 분야"))
            av = Q.QVBoxLayout(app_box)
            apps_text = Q.QTextEdit(); apps_text.setReadOnly(True)
            apps_text.setMaximumHeight(120)
            apps_text.setPlainText(
                _tr_db(str(props.get("applications", "-") or "-")))
            av.addWidget(apps_text)
            r_lay.addWidget(app_box)

            splitter.addWidget(right)
            splitter.setStretchFactor(0, 2)
            splitter.setStretchFactor(1, 1)

            # v2.931: Reference 섹션 — 접고펴기 + 로컬 PDF + URL 검증
            body_layout.addWidget(_h_separator(Q))
            ref_box = Q.QGroupBox()
            ref_box_v = Q.QVBoxLayout(ref_box)
            ref_box_v.setContentsMargins(4, 4, 4, 4); ref_box_v.setSpacing(4)
            # 헤더 (접고펴기 토글)
            ref_header = Q.QHBoxLayout()
            ref_toggle = Q.QToolButton()
            ref_toggle.setStyleSheet(
                "QToolButton { border: none; font-weight: bold; "
                "font-size: 10pt; color: #1a3a6a; padding: 4px; }")
            # v2.992.beta-5: Reference 기본 접힘 (사용자 요청)
            ref_toggle.setArrowType(C.Qt.RightArrow)
            ref_toggle.setText(
                f"  ◆ Reference / MDS ({len(urls) if urls else 0})  ")
            ref_toggle.setToolButtonStyle(C.Qt.ToolButtonTextBesideIcon)
            ref_toggle.setCheckable(True)
            ref_toggle.setChecked(False)
            ref_header.addWidget(ref_toggle)
            ref_header.addStretch(1)
            btn_attach_pdf = Q.QPushButton(_T("MD_PDF_ATTACH", "📎 로컬 PDF 첨부"))
            btn_attach_pdf.setToolTip(
                "Attach a local PDF as a reference.\n"
                "The selected file is copied into data/refs/.")
            btn_attach_pdf.setMaximumWidth(140)
            ref_header.addWidget(btn_attach_pdf)
            ref_box_v.addLayout(ref_header)
            # URL/파일 컨테이너 (토글 대상)
            ref_content = Q.QWidget()
            uv = Q.QVBoxLayout(ref_content)
            uv.setContentsMargins(8, 4, 8, 4)

            # v2.932: URL 검증은 빌드 시점에 외부적으로 (WebFetch) — 런타임 X
            def _make_url_row(vendor, target, is_local=False):
                row = Q.QHBoxLayout()
                # v2.992.beta-5 hotfix6: vendor label can contain Korean
                # (e.g. "Nikon SLM Steel 카탈로그") -> tr_db
                vlbl = Q.QLabel(f"  • {_tr_db(vendor)}")
                vlbl.setStyleSheet("font-weight: bold;")
                vlbl.setMinimumWidth(180)
                row.addWidget(vlbl)
                disp = target if len(target) <= 80 else target[:77] + "..."
                ulbl = Q.QLabel(disp)
                ulbl.setStyleSheet(
                    "color: #0066cc; font-family: Consolas; font-size: 9pt;")
                ulbl.setToolTip(target)
                row.addWidget(ulbl, 1)
                status_lbl = Q.QLabel(_T("MD_UNVERIFIED", "(미검증)"))
                status_lbl.setStyleSheet(
                    "color: #999; font-size: 8pt;")
                status_lbl.setMaximumWidth(110)
                row.addWidget(status_lbl)
                if is_local:
                    try:
                        import os as _os
                        if _os.path.exists(target):
                            status_lbl.setText(_T("MD_LOCAL_OK", "✓ 로컬 OK"))
                            status_lbl.setStyleSheet(
                                "color: #2e7d32; font-size: 8pt;")
                        else:
                            status_lbl.setText(_T("MD_FILE_MISSING", "✗ 파일 없음"))
                            status_lbl.setStyleSheet(
                                "color: #c62828; font-size: 8pt;")
                    except Exception: pass
                    open_btn = Q.QPushButton(_T("MD_BTN_OPEN", "📂 열기"))
                    open_btn.setMaximumWidth(80)
                    def _open_local(p=target):
                        try:
                            import subprocess, os as _os, sys
                            if sys.platform == "win32":
                                _os.startfile(p)
                            elif sys.platform == "darwin":
                                subprocess.Popen(["open", p])
                            else:
                                subprocess.Popen(["xdg-open", p])
                        except Exception as ee:
                            _log(f"open local err: {ee}")
                    open_btn.clicked.connect(_open_local)
                    row.addWidget(open_btn)
                else:
                    # v2.932: in-app URL 검증 제거 — DB 의 모든 URL 은
                    # 빌드 시점에 직접 검증된 것 (or "검증 필요" 마커)
                    status_lbl.setText(_T("MD_EXTERNAL_URL", "(외부 URL)"))
                    status_lbl.setStyleSheet(
                        "color: #666; font-size: 8pt;")
                    cb_btn = Q.QPushButton(_T("MD_BTN_COPY", "📋 복사"))
                    cb_btn.setMaximumWidth(80)
                    def _make_copy(u=target, v=vendor):
                        def _cp():
                            try:
                                app.clipboard().setText(u)
                                Q.QMessageBox.information(
                                    win, "URL copied",
                                    f"{v} URL copied to clipboard")
                            except Exception as ee:
                                _log(f"clipboard err: {ee}")
                        return _cp
                    cb_btn.clicked.connect(_make_copy())
                    row.addWidget(cb_btn)
                return row

            if urls:
                for entry in urls:
                    try:
                        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                            vendor, target = entry[0], entry[1]
                        else:
                            vendor, target = "Reference", str(entry)
                        is_local = (target.lower().endswith(".pdf")
                                      and not target.startswith("http"))
                        uv.addLayout(_make_url_row(vendor, target, is_local))
                    except Exception as e:
                        _log(f"url entry fail: {e}")
            else:
                uv.addWidget(Q.QLabel(_T("MD_NO_REF", "(reference 없음)")))

            ref_box_v.addWidget(ref_content)
            # v2.992.beta-5: 초기 상태에서 ref_content 숨김
            ref_content.setVisible(False)

            def _toggle_ref():
                expanded = ref_toggle.isChecked()
                ref_content.setVisible(expanded)
                ref_toggle.setArrowType(
                    C.Qt.DownArrow if expanded else C.Qt.RightArrow)
            ref_toggle.toggled.connect(_toggle_ref)

            def _on_attach_pdf():
                fn, _ = Q.QFileDialog.getOpenFileName(
                    win, "Attach reference PDF",
                    "", "PDF files (*.pdf);;All files (*)")
                if not fn: return
                try:
                    import os as _os, shutil as _sh
                    # v2.992.beta-5: resource_helper 로 data/ 위치 검색 —
                    #   BUILD_PROTECT 모드에서 %TEMP% 가 아닌 launcher 옆 영구 폴더.
                    try:
                        from resource_helper import get_resource_dir
                        _data_base = get_resource_dir("data")
                    except Exception:
                        # dev fallback
                        _here_d = _os.path.dirname(_os.path.abspath(__file__))
                        _data_base = _os.path.normpath(
                            _os.path.join(_here_d, "..", "..", "data"))
                    refs_dir = _os.path.normpath(
                        _os.path.join(_data_base, "refs",
                                      material_name.replace(" ", "_")))
                    _os.makedirs(refs_dir, exist_ok=True)
                    dst = _os.path.join(refs_dir, _os.path.basename(fn))
                    if _os.path.abspath(fn) != _os.path.abspath(dst):
                        _sh.copy2(fn, dst)
                    uv.addLayout(_make_url_row(
                        "Local PDF (attached)", dst, is_local=True))
                    Q.QMessageBox.information(
                        win, "PDF attached",
                        f"{_os.path.basename(fn)} attached.\n"
                        f"Location: {dst}")
                    _log(f"attach pdf: {dst}")
                except Exception as ee:
                    Q.QMessageBox.warning(
                        win, "PDF attach failed", f"{ee}")
                    _log(f"attach pdf err: {ee}")
            btn_attach_pdf.clicked.connect(_on_attach_pdf)

            body_layout.addWidget(ref_box)

        _build_body(material_name, properties, mds_urls)

        def _on_material_changed(idx):
            if not material_db: return
            new_name = mat_combo.currentText()
            _log(f"material changed -> {new_name}")
            mats = material_db.get("materials", {}) or {}
            new_props = mats.get(new_name, {})
            new_urls = new_props.get("ref_urls", []) or []
            try:
                win.setWindowTitle(f"MDS - {new_name}")
                _build_body(new_name, new_props, new_urls)
            except Exception as e:
                import traceback as _tb
                _log(f"rebuild fail: {e}")
                Q.QMessageBox.warning(win, "Material switch failed", str(e))

        try:
            mat_combo.currentIndexChanged.connect(_on_material_changed)
        except Exception as e:
            _log(f"combo connect fail: {e}")

        def _on_cat_changed(_idx):
            _populate_materials(cat_combo.currentText())
            # _populate_materials blocked signals during the rebuild, so
            # explicitly trigger a body refresh for the first item shown.
            if mat_combo.count() > 0:
                _on_material_changed(mat_combo.currentIndex())
        try:
            cat_combo.currentIndexChanged.connect(_on_cat_changed)
        except Exception as e:
            _log(f"category combo connect fail: {e}")

        foot = Q.QHBoxLayout()
        foot.addStretch()
        btn_close = Q.QPushButton("Close")
        btn_close.setMinimumWidth(100)
        btn_close.clicked.connect(win.close)
        foot.addWidget(btn_close)
        outer.addLayout(foot)

        _open_windows.append(win)
        win.show()
        try: win.raise_(); win.activateWindow()
        except Exception: pass
        _log("=== open_mds_qt SUCCESS ===")
        return True
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        _log(f"!!! open_mds_qt EXCEPTION: {e}")
        _log(tb)