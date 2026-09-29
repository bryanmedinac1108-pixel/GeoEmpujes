"""
Módulo Principal de Interfaz Gráfica (GUI) - Tkinter.
Avanzado: 
- Gestor de Unidades Desacoplado (L, F, P, Gamma).
- Renderizado en segundo plano para capas individuales.
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from modelos import Caso, Carga, Estrato
from calculo import resolver
from exportar import exportar
from graficos import renderizar_perfil, renderizar_presiones

class Aplicacion(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Empujes laterales | Ingeniería civil')
        self.geometry('1350x780') 
        self.minsize(1100, 650)
        
        style = ttk.Style(self)
        if 'clam' in style.theme_names(): style.theme_use('clam')
        style.configure('Title.TLabel', font=('Segoe UI', 18, 'bold'))
        style.configure('Head.TLabel', font=('Segoe UI', 11, 'bold'))
        style.configure('TButton', padding=7)
        
        self.resultado = None
        self.cargas_rows = [] 
        self.last_carga_idx = None 
        
        self.uni_L = tk.StringVar(value='m')
        self.uni_F = tk.StringVar(value='kN')
        self.uni_P = tk.StringVar(value='kPa')
        self.uni_Gamma = tk.StringVar(value='kN/m³')
        
        self.map_L = {'m': 1.0, 'cm': 0.01, 'mm': 0.001, 'ft': 0.3048, 'in': 0.0254}
        self.map_F = {'kN': 1.0, 'MN': 1000.0, 'N': 0.001, 'tonf': 9.80665, 'kgf': 0.00980665, 'lbf': 0.00444822, 'kip': 4.44822}
        self.map_P = {
            'kPa': 1.0, 'MPa': 1000.0, 'Pa': 0.001, 'atm': 101.325, 'bar': 100.0,
            'tonf/m²': 9.80665, 'kgf/cm²': 98.0665, 'kgf/m²': 0.00980665,
            'psf': 0.0478803, 'ksf': 47.8803, 'psi': 6.89476,
            'kN/m²': 1.0, 'MN/m²': 1000.0, 'N/m²': 0.001
        }
        self.map_Gamma = {
            'kN/m³': 1.0, 'MN/m³': 1000.0, 'N/m³': 0.001,
            'tonf/m³': 9.80665, 'kgf/m³': 0.00980665, 'kgf/cm³': 9806.65,
            'g/cm³': 9.80665, 'lbf/ft³ (pcf)': 0.157147, 'kip/ft³ (kcf)': 157.147
        }
        
        self._menu_superior()
        self._layout()
        self._limpiar()  
        
        for var in (self.alpha, self.beta, self.b_base, self.e_pantalla):
            var.trace_add('write', self._actualizar_grafico_muro)
        self.altura.trace_add('write', self._on_altura_trace)

    def _eval_math(self, expr):
        try:
            expr = str(expr).strip().replace(',', '.')
            if expr.startswith('='): expr = expr[1:]
            if not expr: return 0.0
            permitidos = "0123456789+-*/(). "
            if all(c in permitidos for c in expr): return float(eval(expr))
            return float(expr)
        except Exception: return 0.0

    def _float(self, var): 
        return self._eval_math(var.get())

    def _menu_superior(self):
        menu_bar = tk.Menu(self)
        self.config(menu=menu_bar)
        
        archivo_menu = tk.Menu(menu_bar, tearoff=0)
        archivo_menu.add_command(label="Abrir proyecto...", command=self._abrir_proyecto)
        archivo_menu.add_command(label="Guardar proyecto...", command=self._guardar_proyecto)
        archivo_menu.add_separator()
        archivo_menu.add_command(label="Salir", command=self.quit)
        menu_bar.add_cascade(label="Archivo", menu=archivo_menu)
        
        config_menu = tk.Menu(menu_bar, tearoff=0)
        config_menu.add_command(label="Unidades de entrada...", command=self._config_unidades)
        menu_bar.add_cascade(label="Configuración", menu=config_menu)

    def _layout(self):
        outer = ttk.Frame(self, padding=15); outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='Empujes laterales en muros', style='Title.TLabel').pack(anchor='w')
        self.lbl_unidades_sub = ttk.Label(outer, text='Personalizado')
        self.lbl_unidades_sub.pack(anchor='w', pady=(2,10))
        
        bottom = ttk.Frame(outer)
        bottom.pack(side='bottom', fill='x', pady=(12,0))
        ttk.Button(bottom, text='Limpiar datos', command=self._limpiar).pack(side='left')
        
        self.btn_calcular = ttk.Button(bottom, text='Calcular y mostrar resultados', command=self._calcular)
        self.btn_calcular.pack(side='right')
        
        self.btn_exportar = ttk.Button(bottom, text='Exportar Reporte (CSV + PDF)', command=self._exportar, state='disabled')
        self.btn_exportar.pack(side='right', padx=(0, 10))

        self.main_pw_v = ttk.Panedwindow(outer, orient='vertical')
        self.main_pw_v.pack(side='top', fill='both', expand=True)
        
        self.top_pw_h = ttk.Panedwindow(self.main_pw_v, orient='horizontal')
        self.main_pw_v.add(self.top_pw_h, weight=1)
        
        self.frame_perfil = ttk.Frame(self.main_pw_v)
        self.main_pw_v.add(self.frame_perfil, weight=1)
        
        self.frame_tabs = ttk.Frame(self.top_pw_h)
        self.top_pw_h.add(self.frame_tabs, weight=1)
        
        self.tabs = ttk.Notebook(self.frame_tabs)
        self.tabs.pack(fill='both', expand=True)
        
        self.frame_graf_resul = ttk.Frame(self.top_pw_h)
        
        self.general = ttk.Frame(self.tabs, padding=18)
        self.estratos_tab = ttk.Frame(self.tabs, padding=18)
        self.cargas_tab = ttk.Frame(self.tabs, padding=18)
        self.salida = ttk.Frame(self.tabs, padding=12)
        
        for tab, title in ((self.general, '1 · Datos generales'), (self.estratos_tab, '2 · Estratos y agua'),
                          (self.cargas_tab, '3 · Sobrecargas'), (self.salida, '4 · Resultados')):
            self.tabs.add(tab, text=title)
            
        self._general(); self._estratos(); self._cargas(); self._salida()
        self._toggle_metodo(); self._actualizar_textos_unidades() 
        
        self.fig_perfil = Figure(figsize=(10, 3.5), dpi=100, tight_layout=True)
        self.ax_perfil = self.fig_perfil.add_subplot(111); self.ax_perfil.axis('off') 
        self.canvas_perfil = FigureCanvasTkAgg(self.fig_perfil, master=self.frame_perfil)
        self.toolbar_perfil = NavigationToolbar2Tk(self.canvas_perfil, self.frame_perfil)
        self.toolbar_perfil.update()
        self.canvas_perfil.get_tk_widget().pack(side='top', fill='both', expand=True)
        
        self.fig_resul = Figure(figsize=(5, 4), dpi=100, tight_layout=True)
        self.ax_resul = self.fig_resul.add_subplot(111); self.ax_resul.axis('off') 
        
        self.f_capas = ttk.Frame(self.frame_graf_resul)
        self.f_capas.pack(side='top', fill='x', pady=(0,2))
        ttk.Label(self.f_capas, text="Capas visuales:").pack(side='left', padx=(0, 5))
        
        self.vis_suelo = tk.BooleanVar(value=True)
        self.vis_agua = tk.BooleanVar(value=True)
        self.vis_carga = tk.BooleanVar(value=True)
        self.vis_sismo = tk.BooleanVar(value=True)
        self.vis_vectores = tk.BooleanVar(value=True)
        
        self.chk_suelo = ttk.Checkbutton(self.f_capas, text="Suelo", variable=self.vis_suelo, command=self._actualizar_resultados_por_unidad)
        self.chk_suelo.pack(side='left', padx=3)
        self.chk_agua = ttk.Checkbutton(self.f_capas, text="Agua", variable=self.vis_agua, command=self._actualizar_resultados_por_unidad)
        self.chk_agua.pack(side='left', padx=3)
        self.chk_carga = ttk.Checkbutton(self.f_capas, text="Sobrecargas", variable=self.vis_carga, command=self._actualizar_resultados_por_unidad)
        self.chk_carga.pack(side='left', padx=3)
        self.chk_sismo = ttk.Checkbutton(self.f_capas, text="Sismo", variable=self.vis_sismo, command=self._actualizar_resultados_por_unidad)
        self.chk_sismo.pack(side='left', padx=3)
        self.chk_vectores = ttk.Checkbutton(self.f_capas, text="Vectores (y)", variable=self.vis_vectores, command=self._actualizar_resultados_por_unidad)
        self.chk_vectores.pack(side='left', padx=3)

        self.canvas_resul = FigureCanvasTkAgg(self.fig_resul, master=self.frame_graf_resul)
        self.toolbar_resul = NavigationToolbar2Tk(self.canvas_resul, self.frame_graf_resul)
        self.toolbar_resul.update()
        self.canvas_resul.get_tk_widget().pack(side='top', fill='both', expand=True)

    def _entry(self, parent, row, text, value, width=14, column=0):
        lbl = ttk.Label(parent, text=text)
        lbl.grid(row=row, column=column, padx=6, pady=7, sticky='w')
        var = tk.StringVar(value=str(value))
        ent = ttk.Entry(parent, textvariable=var, width=width)
        ent.grid(row=row, column=column+1, padx=6, pady=7, sticky='w')
        def _aplicar_formula(evt): var.set(f"{self._eval_math(var.get()):.3f}")
        ent.bind('<Return>', _aplicar_formula); ent.bind('<FocusOut>', _aplicar_formula)
        return var, lbl, ent

    def _general(self):
        canvas = tk.Canvas(self.general, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.general, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self.canvas_window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True); scrollbar.pack(side="right", fill="y")
        
        canvas.bind("<Configure>", lambda event: canvas.itemconfig(self.canvas_window_id, width=event.width))
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1*(event.delta/120)), "units"))

        f_geo = ttk.LabelFrame(scrollable_frame, text='1. Geometría del Muro', padding=15)
        f_geo.pack(anchor='nw', fill='x', pady=5, padx=5)
        
        ttk.Label(f_geo, text='Tipo de muro').grid(row=0, column=0, sticky='w', padx=6, pady=7)
        self.tipo_muro = tk.StringVar(value='Rectangular')
        self.combo_tipo = ttk.Combobox(f_geo, textvariable=self.tipo_muro, values=['Rectangular', 'Trapezoidal'], state='readonly', width=15)
        self.combo_tipo.grid(row=0, column=1, padx=6, sticky='w')
        self.combo_tipo.bind('<<ComboboxSelected>>', self._cambio_tipo_muro)
        
        self.altura, self.lbl_altura, _ = self._entry(f_geo, 0, 'Altura total H', 5.00, column=2)
        
        ttk.Label(f_geo, text='Modificar dimensiones').grid(row=1, column=0, sticky='w', padx=6, pady=7)
        self.modo_muro = tk.StringVar(value='Genérico')
        combo_modo = ttk.Combobox(f_geo, textvariable=self.modo_muro, values=['Genérico', 'Personalizado'], state='readonly', width=15)
        combo_modo.grid(row=1, column=1, padx=6, sticky='w')
        combo_modo.bind('<<ComboboxSelected>>', self._toggle_campos_muro)
        
        self.b_base, self.lbl_b, self.ent_b = self._entry(f_geo, 2, 'Ancho de base B', 2.0, column=0)
        self.e_pantalla, self.lbl_e, self.ent_e = self._entry(f_geo, 2, 'Espesor pantalla', 0.5, column=2)

        f_ana = ttk.LabelFrame(scrollable_frame, text='2. Condiciones del Análisis', padding=15)
        f_ana.pack(anchor='nw', fill='x', pady=5, padx=5)

        self.beta, _, _ = self._entry(f_ana, 0, 'Ángulo del muro β (°)', 90, column=0)
        self.alpha, _, _ = self._entry(f_ana, 0, 'Ángulo del relleno α (°)', 0, column=2)

        ttk.Label(f_ana, text='Condición').grid(row=1, column=0, sticky='w', padx=6, pady=7)
        self.cond = tk.StringVar(value='activa')
        self.combo_cond = ttk.Combobox(f_ana, textvariable=self.cond, values=['activa','pasiva','reposo'], state='readonly', width=15)
        self.combo_cond.grid(row=1, column=1, padx=6, sticky='w')
        self.combo_cond.bind('<<ComboboxSelected>>', self._cambio_condicion)
        
        ttk.Label(f_ana, text='Método').grid(row=1, column=2, sticky='w', padx=6, pady=7)
        self.metodo = tk.StringVar(value='Rankine')
        self.combo_metodo = ttk.Combobox(f_ana, textvariable=self.metodo, values=['Rankine','Coulomb'], state='readonly', width=15)
        self.combo_metodo.grid(row=1, column=3, padx=6, sticky='w')
        self.combo_metodo.bind('<<ComboboxSelected>>', self._toggle_metodo)

        f_sis = ttk.LabelFrame(scrollable_frame, text='3. Sismo (Mononobe-Okabe)', padding=15)
        f_sis.pack(anchor='nw', fill='x', pady=5, padx=5)

        self.kh, _, _ = self._entry(f_sis, 0, 'kh (0 = estático)', 0, column=0)
        self.kv, _, _ = self._entry(f_sis, 0, 'kv (+ hacia arriba)', 0, column=2)
        
        self._toggle_campos_muro()

    def _cambio_condicion(self, event=None):
        if self.cond.get() == 'reposo':
            self.combo_metodo['values'] = ['Jaky']; self.metodo.set('Jaky')
        else:
            self.combo_metodo['values'] = ['Rankine', 'Coulomb']
            if self.metodo.get() not in ['Rankine', 'Coulomb']: self.metodo.set('Rankine')
        self._toggle_metodo(); self._actualizar_grafico_muro()

    def _toggle_metodo(self, event=None):
        cols = ['#','h','γ','γsat','φ′ (°)','c′','δ (°)']
        if hasattr(self, 'tabla_e'):
            vis_cols = cols[:-1] if self.metodo.get() in ['Rankine', 'Jaky'] else cols
            self.tabla_e.configure(displaycolumns=vis_cols)
            for c in vis_cols:
                self.tabla_e.column(c, width=100, minwidth=50, stretch=True, anchor='center')
            self._actualizar_grafico_muro()

    def _cambio_tipo_muro(self, event=None):
        if self.tipo_muro.get() == 'Trapezoidal':
            if self._float(self.beta) >= 90: self.beta.set('45')
        elif self.tipo_muro.get() == 'Rectangular': self.beta.set('90')
        self._actualizar_grafico_muro()

    def _toggle_campos_muro(self, event=None):
        if self.modo_muro.get() == 'Personalizado':
            self.lbl_b.grid(row=2, column=0, sticky='w', padx=6, pady=7); self.ent_b.grid(row=2, column=1, padx=6, sticky='w')
            self.lbl_e.grid(row=2, column=2, sticky='w', padx=6, pady=7); self.ent_e.grid(row=2, column=3, padx=6, sticky='w')
        else:
            self.lbl_b.grid_forget(); self.ent_b.grid_forget(); self.lbl_e.grid_forget(); self.ent_e.grid_forget()
        self._actualizar_grafico_muro()

    def _tabla(self, parent, cols, height=9):
        f = ttk.Frame(parent); f.pack(fill='both', expand=True, pady=8)
        t = ttk.Treeview(f, columns=cols, show='headings', height=height, selectmode='extended')
        for col in cols: 
            t.heading(col, text=col)
            t.column(col, width=100, minwidth=50, anchor='center', stretch=True)
        s = ttk.Scrollbar(f, orient='vertical', command=t.yview); t.configure(yscroll=s.set)
        t.pack(side='left', fill='both', expand=True); s.pack(side='right', fill='y')
        return t

    def _estratos(self):
        top = ttk.LabelFrame(self.estratos_tab, text='Nivel freático', padding=10); top.pack(fill='x')
        self.agua = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text='Considerar agua', variable=self.agua).grid(row=0, column=0, padx=8)
        self.nf, self.lbl_nf, self.ent_nf = self._entry(top, 1, 'NF', 0.0)
        self.gamma_agua, self.lbl_g_agua, self.ent_g_agua = self._entry(top, 2, 'γagua', 9.81)
        
        self.agua.trace_add('write', self._toggle_agua); self._toggle_agua()
        self.nf.trace_add('write', self._actualizar_grafico_muro)
        
        botones = ttk.Frame(self.estratos_tab)
        botones.pack(side='bottom', fill='x', pady=(5, 0))
        ttk.Button(botones, text='+ Agregar estrato', command=self._agregar_estrato).pack(side='left', padx=3)
        ttk.Button(botones, text='Eliminar seleccionado(s)', command=self._eliminar_estrato).pack(side='left', padx=3)
        ttk.Label(botones, text='(Doble clic para modificar. Shift/Ctrl para multi-selección)').pack(side='left', padx=15)

        self.tabla_e = self._tabla(self.estratos_tab, ['#','h','γ','γsat','φ′ (°)','c′','δ (°)'], height=6)
        self.tabla_e.bind('<Double-1>', lambda e: self._iniciar_edicion_estrato(e, self.tabla_e))
        self.tabla_e.bind('<ButtonPress-1>', self._on_drag_start)
        self.tabla_e.bind('<ButtonRelease-1>', self._on_drag_release)

    def _toggle_agua(self, *args):
        if hasattr(self, 'ent_nf') and hasattr(self, 'ent_g_agua'):
            estado = 'normal' if self.agua.get() else 'disabled'
            self.ent_nf.configure(state=estado); self.ent_g_agua.configure(state=estado)
            self._actualizar_grafico_muro()

    def _on_drag_start(self, event):
        row = self.tabla_e.identify_row(event.y)
        self.drag_data = {'item': row} if row else None

    def _on_drag_release(self, event):
        if not getattr(self, 'drag_data', None) or not self.drag_data.get('item'): return
        target_row = self.tabla_e.identify_row(event.y)
        item = self.drag_data['item']
        if target_row and target_row != item:
            self.tabla_e.move(item, '', self.tabla_e.index(target_row))
            self._renumerar(); self._recalcular_estratos()
        self.drag_data = None

    def _on_altura_trace(self, *args): self._recalcular_estratos()

    def _recalcular_estratos(self):
        h_total = self._float(self.altura)
        if h_total <= 0: return
        
        filas = self.tabla_e.get_children()
        if not filas: return self._actualizar_grafico_muro()
            
        locked_items = [item for item in filas if 'locked' in self.tabla_e.item(item, 'tags')]
        unlocked_items = [item for item in filas if item not in locked_items]
                
        sum_locked = sum(self._eval_math(self.tabla_e.item(item, 'values')[1]) for item in locked_items)
        h_remaining = h_total - sum_locked
        
        if h_remaining < 0 or (not unlocked_items and abs(h_remaining) > 1e-5):
            unlocked_items, locked_items, h_remaining = list(filas), [], h_total
            for item in filas:
                tags = list(self.tabla_e.item(item, 'tags'))
                if 'locked' in tags: tags.remove('locked'); self.tabla_e.item(item, tags=tags)
                
        if unlocked_items:
            h_new = h_remaining / len(unlocked_items)
            for item in unlocked_items:
                vals = list(self.tabla_e.item(item, 'values'))
                vals[1] = f"{h_new:.3f}"
                self.tabla_e.item(item, values=vals)
                
        self._actualizar_grafico_muro()

    def _iniciar_edicion_estrato(self, event, tree):
        if tree.identify("region", event.x, event.y) != "cell": return
        col_idx = int(tree.identify_column(event.x)[1:]) - 1
        item_id = tree.focus()
        if not item_id or col_idx == 0: return 
        
        x, y, w, h = tree.bbox(item_id, tree.identify_column(event.x))
        if hasattr(self, '_editor_activo') and self._editor_activo.winfo_exists(): self._editor_activo.destroy()
        
        editor = ttk.Entry(tree)
        editor.insert(0, tree.item(item_id, 'values')[col_idx])
        editor.select_range(0, tk.END)
        editor.place(x=x, y=y, width=w, height=h); editor.focus()
        self._editor_activo = editor
        
        def guardar_edicion(evt=None):
            if not editor.winfo_exists(): return
            nuevo_val = f"{self._eval_math(editor.get()):.3f}"
            valores = list(tree.item(item_id, 'values'))
            valores[col_idx] = nuevo_val
            
            if col_idx == 1:
                tags = list(tree.item(item_id, 'tags'))
                if 'locked' not in tags: tags.append('locked'); tree.item(item_id, tags=tags)
                
            tree.item(item_id, values=valores); editor.destroy()
            if col_idx == 1: self._recalcular_estratos()
            else: self._actualizar_grafico_muro()
                
        editor.bind('<Return>', guardar_edicion); editor.bind('<FocusOut>', guardar_edicion); editor.bind('<Escape>', lambda e: editor.destroy())

    def _agregar_estrato(self):
        num = len(self.tabla_e.get_children()) + 1
        self.tabla_e.insert('', 'end', values=[num, 0.0, 18, 20, 30, 0, 0])
        self._recalcular_estratos()

    def _eliminar_estrato(self):
        seleccionados = self.tabla_e.selection()
        if not seleccionados: return
        for item_id in seleccionados: self.tabla_e.delete(item_id)
        self._renumerar(); self._recalcular_estratos()

    def _renumerar(self):
        for j, item_id in enumerate(self.tabla_e.get_children(), 1):
            v = list(self.tabla_e.item(item_id, 'values'))
            v[0] = j
            self.tabla_e.item(item_id, values=v)

    def _cargas(self):
        botones = ttk.Frame(self.cargas_tab)
        botones.pack(side='bottom', fill='x', pady=(5, 0))
        ttk.Button(botones, text='+ Agregar sobrecarga', command=self._agregar_carga).pack(side='left', padx=3)
        ttk.Button(botones, text='Eliminar seleccionadas', command=self._eliminar_carga).pack(side='left', padx=3)
        ttk.Label(botones, text='(Shift+Clic en las casillas para rango múltiple)').pack(side='left', padx=15)
        
        header = ttk.Frame(self.cargas_tab)
        header.pack(side='top', fill='x', pady=(5, 2))
        ttk.Label(header, text="Sel", width=4).grid(row=0, column=0, padx=2)
        ttk.Label(header, text="Tipo de Carga", width=15).grid(row=0, column=1, padx=2)
        ttk.Label(header, text="Magnitud", width=12).grid(row=0, column=2, padx=2)
        self.lbl_col_a = ttk.Label(header, text="a (m)", width=12); self.lbl_col_a.grid(row=0, column=3, padx=2)
        self.lbl_col_b = ttk.Label(header, text="B (m)", width=12); self.lbl_col_b.grid(row=0, column=4, padx=2)
        
        self.cargas_inner = ttk.Frame(self.cargas_tab)
        self.cargas_inner.pack(side="top", fill="both", expand=True)

    def _carga_normal_click(self, event, row_data):
        try: self.last_carga_idx = self.cargas_rows.index(row_data)
        except ValueError: pass

    def _carga_shift_click(self, event, row_data):
        try:
            idx = self.cargas_rows.index(row_data)
            if self.last_carga_idx is not None and self.last_carga_idx < len(self.cargas_rows):
                start, end = min(self.last_carga_idx, idx), max(self.last_carga_idx, idx)
                for i in range(start, end + 1): self.cargas_rows[i]['sel'].set(True)
            else:
                row_data['sel'].set(not row_data['sel'].get())
            self.last_carga_idx = idx
            return "break" 
        except ValueError: pass

    def _agregar_carga(self, tipo='franja', mag=150.0, a=0.0, b=2.0):
        row_frame = ttk.Frame(self.cargas_inner)
        row_frame.pack(fill='x', pady=2)
        
        var_sel = tk.BooleanVar(value=False)
        chk_sel = ttk.Checkbutton(row_frame, variable=var_sel)
        chk_sel.grid(row=0, column=0, padx=2)
        
        var_tipo = tk.StringVar(value=tipo)
        cb_tipo = ttk.Combobox(row_frame, textvariable=var_tipo, values=['uniforme', 'puntual', 'lineal', 'franja'], state='readonly', width=13)
        cb_tipo.grid(row=0, column=1, padx=2)
        
        var_mag = tk.StringVar(value=str(mag))
        ent_mag = ttk.Entry(row_frame, textvariable=var_mag, width=12)
        ent_mag.grid(row=0, column=2, padx=2)
        
        var_a = tk.StringVar(value=str(a))
        ent_a = ttk.Entry(row_frame, textvariable=var_a, width=12)
        ent_a.grid(row=0, column=3, padx=2)
        
        var_b = tk.StringVar(value=str(b))
        ent_b = ttk.Entry(row_frame, textvariable=var_b, width=12)
        ent_b.grid(row=0, column=4, padx=2)
        
        def _aplicar_math(evt, variable): variable.set(f"{self._eval_math(variable.get()):.3f}")
            
        ent_mag.bind('<Return>', lambda e: _aplicar_math(e, var_mag)); ent_mag.bind('<FocusOut>', lambda e: _aplicar_math(e, var_mag))
        ent_a.bind('<Return>', lambda e: _aplicar_math(e, var_a)); ent_a.bind('<FocusOut>', lambda e: _aplicar_math(e, var_a))
        ent_b.bind('<Return>', lambda e: _aplicar_math(e, var_b)); ent_b.bind('<FocusOut>', lambda e: _aplicar_math(e, var_b))

        row_data = {'frame': row_frame, 'sel': var_sel, 'tipo': var_tipo, 'mag': var_mag, 'a': var_a, 'b': var_b, 'ent_a': ent_a, 'ent_b': ent_b}
        self.cargas_rows.append(row_data)
        
        chk_sel.bind("<Button-1>", lambda e, r=row_data: self._carga_normal_click(e, r))
        chk_sel.bind("<Shift-Button-1>", lambda e, r=row_data: self._carga_shift_click(e, r))
        
        def _update_state(*args):
            t = var_tipo.get()
            if t == 'uniforme':
                ent_a.configure(state='normal'); var_a.set('')
                ent_b.configure(state='normal'); var_b.set('')
                ent_a.configure(state='disabled'); ent_b.configure(state='disabled')
            elif t in ['puntual', 'lineal']:
                ent_a.configure(state='normal')
                if not var_a.get(): var_a.set('0.0')
                ent_b.configure(state='normal'); var_b.set('')
                ent_b.configure(state='disabled')
            else:
                ent_a.configure(state='normal'); ent_b.configure(state='normal')
                if not var_a.get(): var_a.set('0.0')
                if not var_b.get(): var_b.set('1.0')
            self._actualizar_grafico_muro()
            
        var_tipo.trace_add('write', _update_state)
        var_mag.trace_add('write', lambda *args: self._actualizar_grafico_muro())
        var_a.trace_add('write', lambda *args: self._actualizar_grafico_muro())
        var_b.trace_add('write', lambda *args: self._actualizar_grafico_muro())
        _update_state()

    def _eliminar_carga(self):
        for r in list(self.cargas_rows):
            if r['sel'].get(): r['frame'].destroy(); self.cargas_rows.remove(r)
        self.last_carga_idx = None 
        self._actualizar_grafico_muro()

    def _salida(self):
        arriba = ttk.Frame(self.salida); arriba.pack(side='top', fill='x')
        self.resumen = ttk.Label(arriba, text='Calcula el caso para ver resultados.', style='Head.TLabel'); self.resumen.pack(side='left')
        
        ttk.Label(arriba, text="  |  Presión gráfica de salida:").pack(side='left', padx=(15, 2))
        self.cb_unidad_res = ttk.Combobox(arriba, values=['Misma que entrada'] + list(self.map_P.keys()), state='readonly', width=16)
        self.cb_unidad_res.set('Misma que entrada')
        self.cb_unidad_res.pack(side='left'); self.cb_unidad_res.bind('<<ComboboxSelected>>', lambda e: self._actualizar_resultados_por_unidad())

        self.componentes = ttk.Treeview(self.salida, columns=['Componente','P','y base'], show='headings', height=8)
        self.componentes.heading('Componente', text='Área Desglosada')
        self.componentes.heading('P', text='Fuerza P')
        self.componentes.heading('y base', text='Brazo y')
        self.componentes.column('Componente', width=220, anchor='w')
        self.componentes.column('P', width=120, anchor='center')
        self.componentes.column('y base', width=120, anchor='center')
        self.componentes.pack(side='top', fill='x', pady=8)
        
        self.nota = ttk.Label(self.salida, text='', wraplength=500); self.nota.pack(side='bottom', fill='x', pady=6)
        
        frame_tabla = ttk.Frame(self.salida); frame_tabla.pack(side='top', fill='both', expand=True)
        self.tabla_r = ttk.Treeview(frame_tabla, columns=['z','Estrato','σ′v','K','Suelo','Agua','Carga','Sismo','Total'], show='headings')
        for c in self.tabla_r['columns']: self.tabla_r.heading(c, text=c); self.tabla_r.column(c, width=82, anchor='center')
        s = ttk.Scrollbar(frame_tabla, orient='vertical', command=self.tabla_r.yview); self.tabla_r.configure(yscroll=s.set)
        self.tabla_r.pack(side='left', fill='both', expand=True); s.pack(side='right', fill='y')

    def _config_unidades(self):
        dlg = tk.Toplevel(self); dlg.title("Unidades de Entrada"); dlg.geometry("380x380")
        dlg.transient(self); dlg.grab_set()
        
        ttk.Label(dlg, text="1. Longitud:", font=('Segoe UI', 9, 'bold')).pack(pady=(10,2))
        cb_L = ttk.Combobox(dlg, textvariable=self.uni_L, values=list(self.map_L.keys()), state='readonly'); cb_L.pack()
        
        ttk.Label(dlg, text="2. Fuerza:", font=('Segoe UI', 9, 'bold')).pack(pady=(10,2))
        cb_F = ttk.Combobox(dlg, textvariable=self.uni_F, values=list(self.map_F.keys()), state='readonly'); cb_F.pack()
        
        ttk.Label(dlg, text="3. Presión / Esfuerzo (c', q, gráfica):", font=('Segoe UI', 9, 'bold')).pack(pady=(10,2))
        cb_P = ttk.Combobox(dlg, textvariable=self.uni_P, values=list(self.map_P.keys()), state='readonly'); cb_P.pack()
        
        ttk.Label(dlg, text="4. Peso Específico (γ):", font=('Segoe UI', 9, 'bold')).pack(pady=(10,2))
        cb_Gamma = ttk.Combobox(dlg, textvariable=self.uni_Gamma, values=list(self.map_Gamma.keys()), state='readonly'); cb_Gamma.pack()
        
        def _sugerir_unidades(event):
            L, F = self.uni_L.get(), self.uni_F.get()
            p_sug, g_sug = f"{F}/{L}²", f"{F}/{L}³"
            if p_sug == "kN/m²": p_sug = "kPa"
            elif p_sug == "MN/m²": p_sug = "MPa"
            elif p_sug == "N/m²": p_sug = "Pa"
            
            if p_sug in self.map_P: self.uni_P.set(p_sug)
            if g_sug in self.map_Gamma: self.uni_Gamma.set(g_sug)

        cb_L.bind('<<ComboboxSelected>>', _sugerir_unidades)
        cb_F.bind('<<ComboboxSelected>>', _sugerir_unidades)
        
        def guardar():
            fpe = self.map_Gamma[self.uni_Gamma.get()]
            self.gamma_agua.set(f"{9.80665 / fpe:.4f}".rstrip('0').rstrip('.'))
            self._actualizar_textos_unidades()
            dlg.destroy()
            
        ttk.Button(dlg, text="Aplicar y actualizar tablas", command=guardar).pack(pady=20)
        
    def _actualizar_textos_unidades(self):
        L, F = self.uni_L.get(), self.uni_F.get()
        P, Gamma = self.uni_P.get(), self.uni_Gamma.get()
        
        self.lbl_unidades_sub.config(text=f'Sistema Activo: L [{L}] | F [{F}] | Esf. [{P}] | γ [{Gamma}]')
        self.lbl_b.config(text=f'Ancho de base B ({L})')
        self.lbl_e.config(text=f'Espesor pantalla ({L})')
        self.lbl_altura.config(text=f'Altura total H ({L})')
        self.lbl_nf.config(text=f'NF ({L})')
        self.lbl_g_agua.config(text=f'γagua ({Gamma})')
        
        self.tabla_e.heading('h', text=f'h ({L})')
        self.tabla_e.heading('γ', text=f'γ ({Gamma})')
        self.tabla_e.heading('γsat', text=f'γsat ({Gamma})')
        self.tabla_e.heading('c′', text=f'c′ ({P})')
        
        if hasattr(self, 'lbl_col_a'):
            self.lbl_col_a.config(text=f"a ({L})")
            self.lbl_col_b.config(text=f"B ({L})")
        
        self._actualizar_resultados_por_unidad()

    def _actualizar_resultados_por_unidad(self):
        if not self.resultado: return
        r = self.resultado
        
        L, F = self.uni_L.get(), self.uni_F.get()
        fl, fF = self.map_L[L], self.map_F[F]
        
        out_p_sel = self.cb_unidad_res.get()
        if out_p_sel == 'Misma que entrada':
            fp_out = self.map_P[self.uni_P.get()]
            lbl_p = self.uni_P.get()
        else:
            fp_out = self.map_P[out_p_sel]
            lbl_p = out_p_sel
            
        lbl_F_L = f"{F}/{L}"; lbl_M = f"{F}·{L}/{L}"

        scale_z = 1.0 / fl
        scale_p = 1.0 / fp_out
        scale_P_lineal = 1.0 / (fF / fl)

        self.resumen.configure(text=f'E = {r.total * scale_P_lineal:.3f} {lbl_F_L}    |    M = {r.momento * (1.0/fF):.3f} {lbl_M}    |    y = {r.y * scale_z:.3f} {L}')
        
        for id in self.componentes.get_children(): self.componentes.delete(id)
        self.componentes.heading('P', text=f'Fuerza P ({lbl_F_L})')
        self.componentes.heading('y base', text=f'Brazo y ({L})')
        
        for d in r.detalles:
            if d.fuerza * scale_P_lineal > 0.005:
                F_val = d.fuerza * scale_P_lineal
                y_val = d.y_base * scale_z
                
                # --- FORMATO DE NÚMEROS LIMPIO ---
                circle_num = f"({d.id})"
                
                self.componentes.insert('', 'end', values=[f" {circle_num} {d.componente} ({d.forma})", f'{F_val:.3f}', f'{y_val:.3f}'])

        self.componentes.insert('', 'end', values=['---------------------------------------', '---------', '---------'])
        
        for nombre, vals in [*r.componentes.items(), ('GRAN TOTAL', (r.total, r.momento, r.y))]:
            if vals[0] * scale_P_lineal > 0.005:
                self.componentes.insert('', 'end', values=[f"∑ {nombre.upper()}", f'{vals[0]*scale_P_lineal:.3f}', f'{vals[2]*scale_z:.3f}'])
            
        for id in self.tabla_r.get_children(): self.tabla_r.delete(id)
        self.tabla_r.heading('z', text=f'z ({L})')
        self.tabla_r.heading('σ′v', text=f'σ′v ({lbl_p})')
        self.tabla_r.heading('Suelo', text=f'Suelo ({lbl_p})')
        self.tabla_r.heading('Agua', text=f'Agua ({lbl_p})')
        self.tabla_r.heading('Carga', text=f'Carga ({lbl_p})')
        self.tabla_r.heading('Sismo', text=f'Sismo ({lbl_p})')
        self.tabla_r.heading('Total', text=f'Total ({lbl_p})')

        paso = max(1, len(r.filas)//500)
        for a in r.filas[::paso]:
            self.tabla_r.insert('', 'end', values=[
                f'{a.z * scale_z:.2f}', a.estrato, 
                f'{a.sigma_v * scale_p:.2f}', f'{a.k:.3f}', 
                f'{a.suelo * scale_p:.2f}', f'{a.agua * scale_p:.2f}', 
                f'{a.carga * scale_p:.2f}', f'{a.sismo * scale_p:.2f}', f'{a.total * scale_p:.2f}'
            ])
            
        visibles = {'Suelo': self.vis_suelo.get(), 'Agua': self.vis_agua.get(), 'Sobrecarga': self.vis_carga.get(), 'Sismo': self.vis_sismo.get(), 'Vectores': self.vis_vectores.get()}
        renderizar_presiones(self.ax_resul, r, scale_z, scale_p, lbl_p, L, scale_P_lineal, lbl_F_L, visibles)
        self.canvas_resul.draw_idle()

    def _actualizar_grafico_muro(self, *args):
        try:
            beta_val = self._float(self.beta)
            
            if self.tipo_muro.get() == 'Trapezoidal' and beta_val >= 90:
                def corregir_angulo():
                    self.beta.set('89')
                    messagebox.showwarning("Dato inválido", "El ángulo β para muro trapezoidal debe ser < 90°.")
                self.after_idle(corregir_angulo)
                return

            estratos = [Estrato(*[self._eval_math(x) for x in self.tabla_e.item(id,'values')[1:7]]) for id in self.tabla_e.get_children()]
            
            def _to_f(v): 
                try: return float(str(v).replace(',', '.'))
                except ValueError: return 0.0
            
            cargas_data = []
            for r in self.cargas_rows:
                cargas_data.append((r['tipo'].get(), self._eval_math(r['mag'].get()), self._eval_math(r['a'].get()), self._eval_math(r['b'].get())))
            
            panes = [str(p) for p in self.top_pw_h.panes()]
            if self.resultado is None:
                if str(self.frame_graf_resul) in panes: self.top_pw_h.forget(self.frame_graf_resul)
            else:
                if str(self.frame_graf_resul) not in panes:
                    self.top_pw_h.add(self.frame_graf_resul, weight=1)
                    self.update_idletasks()
                    self.top_pw_h.sashpos(0, int(self.top_pw_h.winfo_width() * 0.55)) 
            
            renderizar_perfil(self.ax_perfil, self._float(self.altura), estratos, cargas_data, self._float(self.nf) if self.agua.get() else None, self._float(self.alpha), beta_val, self.tipo_muro.get(), self.modo_muro.get(), self._float(self.b_base), self._float(self.e_pantalla), self.uni_L.get())
            self.canvas_perfil.draw_idle()
            
            if self.resultado is not None: self._actualizar_resultados_por_unidad()

        except Exception: pass 

    def _calcular(self):
        try:
            fl, fF = self.map_L[self.uni_L.get()], self.map_F[self.uni_F.get()]
            fp = self.map_P[self.uni_P.get()]
            fpe = self.map_Gamma[self.uni_Gamma.get()]

            estratos_si = []
            for id in self.tabla_e.get_children():
                v = self.tabla_e.item(id,'values')
                estratos_si.append(Estrato(self._eval_math(v[1])*fl, self._eval_math(v[2])*fpe, self._eval_math(v[3])*fpe, self._eval_math(v[4]), self._eval_math(v[5])*fp, self._eval_math(v[6])))
                
            if not estratos_si: return messagebox.showerror('Faltan datos', 'Agregue al menos un estrato.')

            cargas_si = []
            for r in self.cargas_rows:
                tipo, mag = r['tipo'].get(), self._eval_math(r['mag'].get())
                if tipo in ['uniforme', 'franja']: mag_si = mag * fp
                elif tipo == 'lineal': mag_si = mag * (fF / fl)
                else: mag_si = mag * fF
                cargas_si.append(Carga(tipo, mag_si, self._eval_math(r['a'].get())*fl, self._eval_math(r['b'].get())*fl))
            
            caso_si = Caso(
                self._float(self.altura) * fl, estratos_si, self.cond.get(), self.metodo.get(),
                self._float(self.nf) * fl if self.agua.get() else None, self._float(self.gamma_agua) * fpe,
                self._float(self.alpha), self._float(self.beta), self._float(self.kh), self._float(self.kv), cargas_si
            )
            self.resultado = resolver(caso_si)
            
            c = self.resultado.componentes
            
            v_suelo = c['Suelo'][0] > 1e-5
            self.vis_suelo.set(v_suelo)
            self.chk_suelo.configure(state='normal' if v_suelo else 'disabled')
            
            v_agua = c['Agua'][0] > 1e-5
            self.vis_agua.set(v_agua)
            self.chk_agua.configure(state='normal' if v_agua else 'disabled')
            
            v_carga = c['Sobrecarga'][0] > 1e-5
            self.vis_carga.set(v_carga)
            self.chk_carga.configure(state='normal' if v_carga else 'disabled')
            
            v_sismo = c['Incremento sísmico'][0] > 1e-5
            self.vis_sismo.set(v_sismo)
            self.chk_sismo.configure(state='normal' if v_sismo else 'disabled')
            
            self.vis_vectores.set(True)
            self.chk_vectores.configure(state='normal')
            
        except Exception as exc: return messagebox.showerror('Revisar los datos', str(exc))
            
        panes = [str(p) for p in self.top_pw_h.panes()]
        if str(self.frame_graf_resul) not in panes:
            self.top_pw_h.add(self.frame_graf_resul, weight=1)
            self.update_idletasks()
            self.top_pw_h.sashpos(0, int(self.top_pw_h.winfo_width() * 0.55))
        
        self.nota.configure(text='  '.join(self.resultado.notas))
        self.tabs.select(self.salida)
        self.btn_exportar.configure(state='normal')
        self._actualizar_grafico_muro()

    def _exportar(self):
        if self.resultado is None: return messagebox.showinfo('Aviso', 'Calcule primero.')
        path = filedialog.asksaveasfilename(title='Nombre base para CSV y PDF', defaultextension='.csv', filetypes=[('CSV','*.csv')])
        if path:
            try:
                L, F = self.uni_L.get(), self.uni_F.get()
                fl, fF = self.map_L[L], self.map_F[F]
                
                out_p_sel = self.cb_unidad_res.get()
                if out_p_sel == 'Misma que entrada':
                    fp_out = self.map_P[self.uni_P.get()]
                    lbl_p = self.uni_P.get()
                else:
                    fp_out = self.map_P[out_p_sel]
                    lbl_p = out_p_sel
                    
                scale_z = 1.0/fl
                scale_p = 1.0/fp_out
                scale_P_lineal = 1.0 / (fF / fl)
                lbl_F_L = f"{F}/{L}"
                
                scale_gamma = 1.0 / self.map_Gamma[self.uni_Gamma.get()]
                lbl_gamma = self.uni_Gamma.get()
                
                rutas_png = {}
                png_main = path.replace('.csv', '.png')
                self.fig_resul.savefig(png_main, dpi=200, bbox_inches='tight') 
                rutas_png['principal'] = png_main
                
                from matplotlib.figure import Figure
                from matplotlib.backends.backend_agg import FigureCanvasAgg
                
                c_res = self.resultado.componentes
                capas = [
                    ('Suelo', 'Suelo', c_res['Suelo'][0], 'Esfuerzos Analíticos - Aislado: Suelo'),
                    ('Agua', 'Agua', c_res['Agua'][0], 'Esfuerzos Analíticos - Aislado: Agua'),
                    ('Sobrecarga', 'Sobrecarga', c_res['Sobrecarga'][0], 'Esfuerzos Analíticos - Aislado: Sobrecargas'),
                    ('Sismo', 'Incremento sísmico', c_res['Incremento sísmico'][0], 'Esfuerzos Analíticos - Aislado: Sismo')
                ]
                
                for clave_vis, clave_comp, magnitud, titulo in capas:
                    if magnitud * scale_P_lineal > 1e-5:
                        fig_tmp = Figure(figsize=(5, 4), dpi=200, tight_layout=True)
                        canvas_tmp = FigureCanvasAgg(fig_tmp)
                        ax_tmp = fig_tmp.add_subplot(111)
                        
                        vis_aislado = {'Suelo': False, 'Agua': False, 'Sobrecarga': False, 'Sismo': False, 'Vectores': True}
                        vis_aislado[clave_vis] = True
                        
                        renderizar_presiones(ax_tmp, self.resultado, scale_z, scale_p, lbl_p, L, scale_P_lineal, lbl_F_L, vis_aislado, titulo)
                        path_aislado = path.replace('.csv', f'_{clave_vis.lower()}.png')
                        fig_tmp.savefig(path_aislado, bbox_inches='tight')
                        rutas_png[clave_vis.lower()] = path_aislado
                
                archivos = exportar(self.resultado, path, rutas_png, scale_z, scale_p, scale_gamma, L, lbl_p, lbl_gamma)
                messagebox.showinfo('Reporte Generado', '\n'.join(map(str, archivos)))
            except OSError as exc: messagebox.showerror('Error', str(exc))

    def _limpiar(self):
        self.tipo_muro.set('Rectangular'); self.modo_muro.set('Genérico')
        self._toggle_campos_muro()
        for v, x in ((self.altura, 5.0), (self.beta, 90), (self.alpha, 0), (self.kh, 0), (self.kv, 0), (self.nf, 0), (self.b_base, 2.0), (self.e_pantalla, 0.5)):
            v.set(str(x))
            
        self.uni_L.set('m')
        self.uni_F.set('kN')
        self.uni_P.set('kPa')
        self.uni_Gamma.set('kN/m³')
        fpe = self.map_Gamma[self.uni_Gamma.get()]
        self.gamma_agua.set(f"{9.80665 / fpe:.4f}".rstrip('0').rstrip('.')) 
        
        self.cond.set('activa'); self._cambio_condicion()  
        self.agua.set(False)  
        for id in self.tabla_e.get_children(): self.tabla_e.delete(id)
        for r in list(self.cargas_rows): r['frame'].destroy()
        self.cargas_rows.clear()
        
        self.vis_suelo.set(True); self.vis_agua.set(True); self.vis_carga.set(True); self.vis_sismo.set(True); self.vis_vectores.set(True)
        if hasattr(self, 'chk_suelo'):
            self.chk_suelo.configure(state='normal'); self.chk_agua.configure(state='normal')
            self.chk_carga.configure(state='normal'); self.chk_sismo.configure(state='normal'); self.chk_vectores.configure(state='normal')
        
        self.last_carga_idx = None
        if hasattr(self, 'btn_exportar'): self.btn_exportar.configure(state='disabled')
        self.resultado = None; self._recalcular_estratos(); self.tabs.select(self.general)

    def _guardar_proyecto(self):
        datos = {
            "unidades": {"L": self.uni_L.get(), "F": self.uni_F.get(), "P": self.uni_P.get(), "Gamma": self.uni_Gamma.get(), "out_P": self.cb_unidad_res.get()},
            "general": {
                "tipo_muro": self.tipo_muro.get(), "modo_muro": self.modo_muro.get(),
                "b_base": self.b_base.get(), "e_pantalla": self.e_pantalla.get(),
                "altura": self.altura.get(), "beta": self.beta.get(), "alpha": self.alpha.get(),
                "cond": self.cond.get(), "metodo": self.metodo.get(),
                "kh": self.kh.get(), "kv": self.kv.get()
            },
            "agua": { "considerar": self.agua.get(), "nf": self.nf.get(), "gamma_agua": self.gamma_agua.get() },
            "estratos": [self.tabla_e.item(id, 'values') for id in self.tabla_e.get_children()],
            "cargas": [[r['tipo'].get(), r['mag'].get(), r['a'].get(), r['b'].get()] for r in self.cargas_rows]
        }
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Archivos JSON", "*.json")])
        if path:
            with open(path, 'w', encoding='utf-8') as f: json.dump(datos, f, indent=4)
                
    def _abrir_proyecto(self):
        path = filedialog.askopenfilename(filetypes=[("Archivos JSON", "*.json")])
        if path:
            with open(path, 'r', encoding='utf-8') as f: datos = json.load(f)
            
            uni = datos.get("unidades", {})
            self.uni_L.set(uni.get("L", "m")); self.uni_F.set(uni.get("F", "kN"))
            self.uni_P.set(uni.get("P", "kPa")); self.uni_Gamma.set(uni.get("Gamma", "kN/m³"))
            self._actualizar_textos_unidades()
            self.cb_unidad_res.set(uni.get("out_P", "Misma que entrada"))
            
            gen = datos.get("general", {})
            self.tipo_muro.set(gen.get("tipo_muro", "Rectangular")); self.modo_muro.set(gen.get("modo_muro", "Genérico"))
            self.b_base.set(gen.get("b_base", "2.0")); self.e_pantalla.set(gen.get("e_pantalla", "0.5"))
            self.altura.set(gen.get("altura", "5.00")); self.beta.set(gen.get("beta", "90")); self.alpha.set(gen.get("alpha", "0"))
            
            self.cond.set(gen.get("cond", "activa")); self._cambio_condicion()
            self.metodo.set(gen.get("metodo", "Rankine")); self._toggle_metodo()
            self.kh.set(gen.get("kh", "0")); self.kv.set(gen.get("kv", "0"))
            
            ag = datos.get("agua", {})
            self.agua.set(ag.get("considerar", False)); self.nf.set(ag.get("nf", "0.0")); self.gamma_agua.set(ag.get("gamma_agua", "9.81"))
            
            for id in self.tabla_e.get_children(): self.tabla_e.delete(id)
            for est in datos.get("estratos", []): 
                vals = list(est)
                self.tabla_e.insert('', 'end', values=vals, tags=('locked',))
                
            for r in list(self.cargas_rows): r['frame'].destroy()
            self.cargas_rows.clear()
            self.last_carga_idx = None
            for car in datos.get("cargas", []): 
                self._agregar_carga(tipo=car[0], mag=car[1], a=car[2], b=car[3])
                
            self.resultado = None
            self.btn_exportar.configure(state='disabled')
            self._recalcular_estratos()

if __name__ == '__main__':
    app = Aplicacion()
    app.mainloop()