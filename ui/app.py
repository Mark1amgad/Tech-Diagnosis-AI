import sys
import json
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QPushButton, QScrollArea, 
                               QCheckBox, QTextEdit, QSplitter, QFrame, QGraphicsDropShadowEffect,
                               QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal, QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup, QParallelAnimationGroup, QSize
from PySide6.QtGui import QPalette, QColor, QFont, QIcon

from engine.inference_engine import ForwardChainingEngine
from engine.explanation import ExplanationSystem

# ==========================================
# CONFIGURATION
# ==========================================
# Toggle this to False to safely disable all UI animations.
ENABLE_ANIMATIONS = True

# Colors
BACKGROUND_COLOR = "#232323"
PANEL_COLOR = "#111827"
ACCENT_COLOR = "#3b82f6"
NEON_COLOR = "#06b6d4"      # Cyan for neon glows
TEXT_MUTED = "#94a3b8"
ACCENT_GREEN = "#22c55e"
TEXT_LIGHT = "#ffffff"


class InferenceWorker(QThread):
    finished_inference = Signal(dict, list)
    
    def __init__(self, engine, initial_facts):
        super().__init__()
        self.engine = engine
        self.initial_facts = initial_facts
        
    def run(self):
        memory, trace_graph = self.engine.infer(self.initial_facts)
        self.finished_inference.emit(memory, trace_graph)


class DiagnosisApp(QMainWindow):
    def __init__(self, facts_path, rules_path, icon_path=None):
        super().__init__()
        self.facts_path = facts_path
        self.rules_path = rules_path
        self.icon_path = icon_path
        
        self.engine = ForwardChainingEngine(self.rules_path)
        self.explainer = ExplanationSystem()
        self.symptom_vars = {}
        
        with open(self.facts_path, 'r', encoding='utf-8') as f:
            self.available_facts = json.load(f)
            
        self.setWindowTitle("Tech Diagnosis AI")
        self.resize(1200, 800)
        
        if self.icon_path and os.path.exists(self.icon_path):
            self.setWindowIcon(QIcon(self.icon_path))
            
        self.setup_ui()
        self.setup_animations()
        
    def setup_ui(self):
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)
        
        # --- Top Section ---
        top_section = QWidget()
        top_layout = QVBoxLayout(top_section)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("Tech Diagnosis AI")
        title_font = QFont("Segoe UI", 24, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        
        subtitle_label = QLabel("Knowledge-Based Expert System")
        subtitle_font = QFont("Segoe UI", 18)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignCenter)
        
        top_layout.addWidget(title_label)
        top_layout.addWidget(subtitle_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        
        self.btn_diagnose = QPushButton("Diagnose")
        self.btn_diagnose.setCursor(Qt.PointingHandCursor)
        self.btn_diagnose.setMinimumSize(QSize(120, 40))
        self.btn_diagnose.setStyleSheet(f"""
            QPushButton {{
                background-color: #353535;
                color: {NEON_COLOR};
                font-family: 'Segoe UI';
                font-size: 14px;
                font-weight: bold;
                padding: 8px 24px;
                border: 1px solid {NEON_COLOR};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #454545;
            }}
            QPushButton:pressed {{
                background-color: #252525;
            }}
            QPushButton:disabled {{
                color: {TEXT_MUTED};
                border: 1px solid {TEXT_MUTED};
            }}
        """)
        self.btn_diagnose.clicked.connect(self.on_diagnose_clicked)
        # Hook for scale animations on press/release
        self.btn_diagnose.pressed.connect(self.on_btn_diagnose_pressed)
        self.btn_diagnose.released.connect(self.on_btn_diagnose_released)
        
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.setMinimumSize(QSize(100, 40))
        self.btn_reset.setStyleSheet(f"""
            QPushButton {{
                background-color: #353535;
                color: #ffffff;
                font-family: 'Segoe UI';
                font-size: 14px;
                padding: 8px 24px;
                border: 1px solid #555555;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #454545;
            }}
        """)
        self.btn_reset.clicked.connect(self.reset_ui)
        
        btn_layout.addWidget(self.btn_diagnose)
        btn_layout.addWidget(self.btn_reset)
        top_layout.addLayout(btn_layout)
        
        main_layout.addWidget(top_section)
        
        # Divider line
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(divider)
        
        # --- Main Splitter Section ---
        self.splitter = QSplitter(Qt.Horizontal)
        
        # Left Panel (Symptoms)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        symptoms_label = QLabel("Symptoms")
        symptoms_label.setFont(QFont("Segoe UI", 18))
        symptoms_label.setStyleSheet("padding-bottom: 10px;")
        left_layout.addWidget(symptoms_label)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        scroll_widget = QWidget()
        self.checkbox_layout = QVBoxLayout(scroll_widget)
        self.checkbox_layout.setAlignment(Qt.AlignTop)
        
        for fact in self.available_facts:
            chk = QCheckBox(fact['description'])
            chk.setStyleSheet(f"QCheckBox {{ color: {ACCENT_COLOR}; font-family: 'Segoe UI'; font-size: 14px; padding: 4px; }}")
            chk.toggled.connect(lambda checked, c=chk: self.animate_checkbox_pulse(c))
            self.symptom_vars[fact['id']] = chk
            self.checkbox_layout.addWidget(chk)
            
        self.scroll_area.setWidget(scroll_widget)
        left_layout.addWidget(self.scroll_area)
        
        # Center Panel (Results)
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        
        results_label = QLabel("Results")
        results_label.setFont(QFont("Segoe UI", 18))
        results_label.setStyleSheet("padding-bottom: 10px;")
        center_layout.addWidget(results_label)
        
        self.accuracy_bar = QProgressBar()
        self.accuracy_bar.setRange(0, 100)
        self.accuracy_bar.setValue(0)
        self.accuracy_bar.setTextVisible(True)
        self.accuracy_bar.setFormat("Confidence: %p%")
        self.accuracy_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #444;
                border-radius: 4px;
                background-color: {BACKGROUND_COLOR};
                text-align: center;
                color: #ffffff;
                font-family: 'Segoe UI';
                font-weight: bold;
                height: 20px;
                margin-bottom: 10px;
            }}
            QProgressBar::chunk {{
                background-color: {NEON_COLOR};
                border-radius: 3px;
            }}
        """)
        self.accuracy_bar.hide()
        center_layout.addWidget(self.accuracy_bar)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setStyleSheet(f"QTextEdit {{ background-color: {BACKGROUND_COLOR}; font-family: 'Segoe UI'; font-size: 14px; border: 1px solid #444; border-radius: 4px; padding: 10px; }}")
        center_layout.addWidget(self.results_text)
        
        # Right Panel (Explanation)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        explanation_label = QLabel("Explanation")
        explanation_label.setFont(QFont("Segoe UI", 18))
        explanation_label.setStyleSheet("padding-bottom: 10px;")
        right_layout.addWidget(explanation_label)
        
        self.explanation_text = QTextEdit()
        self.explanation_text.setReadOnly(True)
        self.explanation_text.setStyleSheet(f"QTextEdit {{ background-color: {BACKGROUND_COLOR}; font-family: 'Consolas'; font-size: 13px; border: 1px solid #444; border-radius: 4px; padding: 10px; }}")
        right_layout.addWidget(self.explanation_text)
        
        # Add to splitter
        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(center_panel)
        self.splitter.addWidget(right_panel)
        
        left_panel.setMinimumWidth(300)
        center_panel.setMinimumWidth(400)
        right_panel.setMinimumWidth(300)
        
        self.splitter.setSizes([400, 400, 400])
        main_layout.addWidget(self.splitter, stretch=1)

    # ==========================================
    # ANIMATION HELPERS
    # ==========================================
    def setup_animations(self):
        if not ENABLE_ANIMATIONS:
            return
            
        # 1. Primary Button Glow
        self.btn_shadow = QGraphicsDropShadowEffect(self)
        self.btn_shadow.setBlurRadius(15)
        self.btn_shadow.setColor(QColor(NEON_COLOR))
        self.btn_shadow.setOffset(0, 0)
        self.btn_diagnose.setGraphicsEffect(self.btn_shadow)
        
        # 2. Results Panel Glow (Idle)
        self.results_shadow = QGraphicsDropShadowEffect(self)
        self.results_shadow.setBlurRadius(0)
        self.results_shadow.setColor(QColor(NEON_COLOR))
        self.results_shadow.setOffset(0, 0)
        self.results_text.setGraphicsEffect(self.results_shadow)
        
        # Looping Animation for Results Pulse
        self.results_pulse_anim = QPropertyAnimation(self.results_shadow, b"blurRadius")
        self.results_pulse_anim.setDuration(600)
        self.results_pulse_anim.setStartValue(0)
        self.results_pulse_anim.setEndValue(20)
        self.results_pulse_anim.setEasingCurve(QEasingCurve.InOutSine)
        
        self.results_pulse_down_anim = QPropertyAnimation(self.results_shadow, b"blurRadius")
        self.results_pulse_down_anim.setDuration(600)
        self.results_pulse_down_anim.setStartValue(20)
        self.results_pulse_down_anim.setEndValue(0)
        self.results_pulse_down_anim.setEasingCurve(QEasingCurve.InOutSine)
        
        self.results_pulse_group = QSequentialAnimationGroup(self)
        self.results_pulse_group.addAnimation(self.results_pulse_anim)
        self.results_pulse_group.addAnimation(self.results_pulse_down_anim)
        self.results_pulse_group.setLoopCount(-1) # Loop indefinitely
        
        # 3. Explanation Panel Glow (Idle)
        self.explanation_shadow = QGraphicsDropShadowEffect(self)
        self.explanation_shadow.setBlurRadius(0)
        self.explanation_shadow.setColor(QColor(NEON_COLOR))
        self.explanation_shadow.setOffset(0, 0)
        self.explanation_text.setGraphicsEffect(self.explanation_shadow)

    def on_btn_diagnose_pressed(self):
        if not ENABLE_ANIMATIONS: return
        # Shrink slightly and reduce glow
        self.btn_diagnose.setMinimumSize(QSize(116, 38))
        self.btn_shadow.setBlurRadius(5)
        
    def on_btn_diagnose_released(self):
        if not ENABLE_ANIMATIONS: return
        # Restore size and glow
        self.btn_diagnose.setMinimumSize(QSize(120, 40))
        self.btn_shadow.setBlurRadius(15)

    def start_results_pulse(self):
        if ENABLE_ANIMATIONS and self.results_pulse_group.state() != QSequentialAnimationGroup.Running:
            self.results_text.setStyleSheet(f"QTextEdit {{ background-color: {BACKGROUND_COLOR}; font-family: 'Segoe UI'; font-size: 14px; border: 1px solid {NEON_COLOR}; border-radius: 4px; padding: 10px; }}")
            self.results_pulse_group.start()
            
    def stop_results_pulse(self):
        if ENABLE_ANIMATIONS:
            self.results_pulse_group.stop()
            # Fade out gracefully
            anim = QPropertyAnimation(self.results_shadow, b"blurRadius", self)
            anim.setDuration(300)
            anim.setEndValue(0)
            anim.start()
            self.results_text.setStyleSheet(f"QTextEdit {{ background-color: {BACKGROUND_COLOR}; font-family: 'Segoe UI'; font-size: 14px; border: 1px solid #444; border-radius: 4px; padding: 10px; }}")

    def trigger_explanation_flash(self):
        if ENABLE_ANIMATIONS:
            self.explanation_text.setStyleSheet(f"QTextEdit {{ background-color: {BACKGROUND_COLOR}; font-family: 'Consolas'; font-size: 13px; border: 1px solid {NEON_COLOR}; border-radius: 4px; padding: 10px; }}")
            
            anim_up = QPropertyAnimation(self.explanation_shadow, b"blurRadius", self)
            anim_up.setDuration(250)
            anim_up.setStartValue(0)
            anim_up.setEndValue(20)
            anim_up.setEasingCurve(QEasingCurve.OutCubic)
            
            anim_down = QPropertyAnimation(self.explanation_shadow, b"blurRadius", self)
            anim_down.setDuration(400)
            anim_down.setStartValue(20)
            anim_down.setEndValue(0)
            anim_down.setEasingCurve(QEasingCurve.InCubic)
            
            group = QSequentialAnimationGroup(self)
            group.addAnimation(anim_up)
            group.addAnimation(anim_down)
            
            # Reset border when done
            group.finished.connect(lambda: self.explanation_text.setStyleSheet(f"QTextEdit {{ background-color: {BACKGROUND_COLOR}; font-family: 'Consolas'; font-size: 13px; border: 1px solid #444; border-radius: 4px; padding: 10px; }}"))
            group.start()

    def animate_checkbox_pulse(self, checkbox):
        if not ENABLE_ANIMATIONS: return
        
        # Apply shadow effect if it doesn't exist
        effect = checkbox.graphicsEffect()
        if not effect:
            effect = QGraphicsDropShadowEffect(checkbox)
            effect.setColor(QColor(ACCENT_COLOR))
            effect.setOffset(0, 0)
            checkbox.setGraphicsEffect(effect)
            
        anim_up = QPropertyAnimation(effect, b"blurRadius", checkbox)
        anim_up.setDuration(150)
        anim_up.setStartValue(0)
        anim_up.setEndValue(15)
        
        anim_down = QPropertyAnimation(effect, b"blurRadius", checkbox)
        anim_down.setDuration(250)
        anim_down.setStartValue(15)
        anim_down.setEndValue(0)
        
        group = QSequentialAnimationGroup(checkbox)
        group.addAnimation(anim_up)
        group.addAnimation(anim_down)
        group.start()

    # ==========================================
    # LOGIC
    # ==========================================
    def reset_ui(self):
        for chk in self.symptom_vars.values():
            chk.setChecked(False)
        self.results_text.clear()
        self.explanation_text.clear()
        self.accuracy_bar.hide()
        self.accuracy_bar.setValue(0)
        if ENABLE_ANIMATIONS:
            self.stop_results_pulse()

    def on_diagnose_clicked(self):
        initial_facts = {}
        for fact_id, chk in self.symptom_vars.items():
            if chk.isChecked():
                name = next((f['description'] for f in self.available_facts if f['id'] == fact_id), fact_id)
                initial_facts[fact_id] = {
                    'value': True,
                    'cf': 1.0,
                    'name': name,
                    'is_inferred': False,
                    'specificity': 0,
                    'priority': 0
                }
                
        if not initial_facts:
            self.results_text.setHtml(f"<span style='color:{TEXT_MUTED};'>Please select at least one symptom.</span>")
            self.explanation_text.clear()
            self.accuracy_bar.hide()
            return
            
        self.btn_diagnose.setEnabled(False)
        self.accuracy_bar.hide()
        self.results_text.setHtml(f"<span style='color:{TEXT_MUTED};'>Analyzing...<br>Evaluating rule chains...</span>")
        self.explanation_text.setHtml(f"<span style='color:{TEXT_MUTED};'>Building reasoning graph...<br>Mapping dependencies...</span>")
        
        self.start_results_pulse()
        
        self.worker = InferenceWorker(self.engine, initial_facts)
        self.worker.finished_inference.connect(self.update_ui_with_results)
        self.worker.start()

    def update_ui_with_results(self, memory, trace_graph):
        self.stop_results_pulse()
        self.trigger_explanation_flash()
        
        self.btn_diagnose.setEnabled(True)
        
        issues = []
        causes = []
        recommendations = []
        
        for fact_id, data in memory.items():
            if not data.get('is_inferred', False): continue
            layer = data.get('layer', 'unknown')
            item = (fact_id, data)
            if layer == 'issue': issues.append(item)
            elif layer == 'cause': causes.append(item)
            elif layer == 'recommendation': recommendations.append(item)
            
        sort_key = lambda x: (x[1]['cf'], x[1]['specificity'], x[1]['priority'])
        issues.sort(key=sort_key, reverse=True)
        causes.sort(key=sort_key, reverse=True)
        recommendations.sort(key=sort_key, reverse=True)
        
        has_results = False
        res_html = ""
        
        if recommendations:
            has_results = True
            res_html += f"<h3 style='color:{ACCENT_COLOR};'>RECOMMENDED ACTIONS</h3>"
            for i, (f_id, data) in enumerate(recommendations):
                color = ACCENT_GREEN if i == 0 else TEXT_LIGHT
                res_html += f"<span style='color:{color};'>[CF: {data['cf']:.2f}] {data['name']}</span><br>"
            res_html += "<br>"
            
        if causes:
            has_results = True
            res_html += f"<h3 style='color:{ACCENT_COLOR};'>ROOT CAUSES</h3>"
            for i, (f_id, data) in enumerate(causes):
                color = ACCENT_GREEN if (not recommendations and i == 0) else TEXT_LIGHT
                res_html += f"<span style='color:{color};'>[CF: {data['cf']:.2f}] {data['name']}</span><br>"
            res_html += "<br>"
            
        if issues:
            has_results = True
            res_html += f"<h3 style='color:{ACCENT_COLOR};'>DETECTED ISSUES</h3>"
            for i, (f_id, data) in enumerate(issues):
                color = ACCENT_GREEN if (not recommendations and not causes and i == 0) else TEXT_LIGHT
                res_html += f"<span style='color:{color};'>[CF: {data['cf']:.2f}] {data['name']}</span><br>"
                
        if not has_results:
            res_html = f"<span style='color:{TEXT_MUTED};'>No specific issues or recommendations found.<br>Try selecting more symptoms.</span>"
            self.accuracy_bar.hide()
        else:
            # Determine top CF
            top_cf = 0.0
            if recommendations:
                top_cf = recommendations[0][1]['cf']
            elif causes:
                top_cf = causes[0][1]['cf']
            elif issues:
                top_cf = issues[0][1]['cf']
                
            if top_cf > 0:
                self.accuracy_bar.show()
                if ENABLE_ANIMATIONS:
                    self.accuracy_anim = QPropertyAnimation(self.accuracy_bar, b"value", self)
                    self.accuracy_anim.setDuration(800)
                    self.accuracy_anim.setStartValue(0)
                    self.accuracy_anim.setEndValue(int(top_cf * 100))
                    self.accuracy_anim.setEasingCurve(QEasingCurve.OutCubic)
                    self.accuracy_anim.start()
                else:
                    self.accuracy_bar.setValue(int(top_cf * 100))
            
        self.results_text.setHtml(res_html)
        
        exp_html = ""
        for layer_group in [recommendations, causes, issues]:
            for f_id, data in layer_group:
                exp_html += f"<b style='color:{ACCENT_COLOR};'>--- Reasoning for: {data['name']} ---</b><br>"
                exp_str = self.explainer.build_graph_explanation(memory, trace_graph, f_id)
                
                for line in exp_str.split('\n'):
                    indent_count = len(line) - len(line.lstrip(' '))
                    indent_html = "&nbsp;" * indent_count
                    stripped = line.lstrip(' ')
                    
                    if "(Initial User Input)" in stripped:
                        exp_html += f"{indent_html}<span style='color:{ACCENT_GREEN};'>{stripped}</span><br>"
                    elif "* Inferred" in stripped:
                        exp_html += f"{indent_html}<span style='color:{TEXT_LIGHT};'>{stripped}</span><br>"
                    else:
                        exp_html += f"{indent_html}<span style='color:{TEXT_MUTED};'>{stripped}</span><br>"
                exp_html += "<br>"
                
        self.explanation_text.setHtml(exp_html)


def launch_app():
    # Set Windows App User Model ID so the taskbar displays the custom icon properly
    if sys.platform == 'win32':
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("NewMansouraUniversity.KBSProject.TechDiagnosisAI.1.0")
        except Exception:
            pass

    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_dir = sys._MEIPASS
    else:
        # Running from source
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    facts_path = os.path.join(base_dir, 'knowledge_base', 'facts.json')
    rules_path = os.path.join(base_dir, 'knowledge_base', 'rules.json')
    icon_path = os.path.join(base_dir, 'icon.ico')
    
    app = QApplication(sys.argv + ['-platform', 'windows:darkmode=2'])
    app.setStyle('Fusion')
    
    darkPalette = QPalette()
    darkPalette.setColor(QPalette.Window, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.WindowText, Qt.white)
    darkPalette.setColor(QPalette.Base, QColor(35, 35, 35))
    darkPalette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
    darkPalette.setColor(QPalette.ToolTipText, Qt.white)
    darkPalette.setColor(QPalette.Text, Qt.white)
    darkPalette.setColor(QPalette.Button, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.ButtonText, Qt.white)
    darkPalette.setColor(QPalette.BrightText, Qt.red)
    darkPalette.setColor(QPalette.Link, QColor(42, 130, 218))
    darkPalette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    darkPalette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(darkPalette)
    
    window = DiagnosisApp(facts_path, rules_path, icon_path=icon_path)
    window.show()
    sys.exit(app.exec())
