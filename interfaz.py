"""
Módulo Principal de Interfaz Gráfica (GUI) - Tkinter.
Orquesta la ventana, tablas interactivas, menús y la conexión entre 
el motor de cálculo (calculo.py) y el motor de renderizado (graficos.py).

Funcionalidades principales:
- Interfaz adaptable y reactiva (actualiza gráficas al vuelo).
- Manejo inteligente de alturas de estratos distribuidas en función de H.
- Ocultamiento dinámico de parámetros (ej. delta se oculta en Rankine).
- Conversor de unidades de resultados en tiempo real (kPa, Pa, MPa, etc.).
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Importaciones de los módulos locales del proyecto
from modelos import Caso, Carga, Estrato
from calculo import resolver
from exportar import exportar
from graficos import renderizar_perfil, renderizar_presiones

class Aplicacion(tk.Tk):
    """Clase principal que hereda de tk.Tk para inicializar la ventana de Windows."""
    
    def __init__(self):
        super().__init__()
        # Configuración básica de la ventana
        self.title('Empujes laterales | Ingeniería civil')
        self.geometry('1350x780') 
        self.minsize(1100, 650)
        
        # Aplicar un tema moderno a los componentes (widgets) de la interfaz
        style = ttk.Style(self)
        if 'clam' in style.theme_names(): style.theme_use('clam')
        style.configure('Title.TLabel', font=('Segoe UI', 18, 'bold'))
        style.configure('Head.TLabel', font=('Segoe UI', 11, 'bold'))
        style.configure('TButton', padding=7)
        
        # Variables de estado global
        self.resultado = None            # Guardará el objeto 'Resultado' tras calcular
        self.sistema_unidades = 'SI'     # Sistema base inicial
        
        # Iniciar la construcción visual
        self._menu_superior()
        self._layout()
        self._limpiar()  
        
        # Trazos (Traces): Permiten ejecutar una función automáticamente si el usuario teclea un dato
        for var in (self.alpha, self.beta, self.nf, self.agua, self.b_base, self.e_pantalla):
            var.trace_add('write', self._actualizar_grafico_muro)
            
        # Trazo especial para H: si cambia la altura total, se redistribuyen los estratos
        self.altura.trace_add('write', self._on_altura_trace)

    def _menu_superior(self):
        """Crea la barra de menú superior nativa de Windows (Archivo, Configuración)."""
        menu_bar = tk.Menu(self)
        self.config(menu=menu_bar)
        
        # Submenú 'Archivo'
        archivo_menu = tk.Menu(menu_bar, tearoff=0)
        archivo_menu.add_command(label="Abrir proyecto...", command=self._abrir_proyecto)
        archivo_menu.add_command(label="Guardar proyecto...", command=self._guardar_proyecto)
        archivo_menu.add_separator()
        archivo_menu.add_command(label="Salir", command=self.quit)
        menu_bar.add_cascade(label="Archivo", menu=archivo_menu)
        
        # Submenú 'Configuración'
        config_menu = tk.Menu(menu_bar, tearoff=0)
        config_menu.add_command(label="Unidades...", command=self._config_unidades)
        menu_bar.add_cascade(label="Configuración", menu=config_menu)

    def _layout(self):
        """Estructura la ventana en zonas, paneles ajustables y pestañas."""
        outer = ttk.Frame(self, padding=15); outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='Empujes laterales en muros', style='Title.TLabel').pack(anchor='w')
        self.lbl_unidades_sub = ttk.Label(outer, text='Unidades SI · resultados horizontales por metro de muro')
        self.lbl_unidades_sub.pack(anchor='w', pady=(2,10))
        
        # Zona inferior de botones principales
        bottom = ttk.Frame(outer)
        bottom.pack(side='bottom', fill='x', pady=(12,0))
        ttk.Button(bottom, text='Limpiar datos', command=self._limpiar).pack(side='left')
        ttk.Button(bottom, text='Calcular y mostrar resultados', command=self._calcular).pack(side='right')

        # Paneles divisores (Panedwindow) para permitir arrastrar y cambiar tamaños
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
        
        # Creación de las 4 Pestañas
        self.general = ttk.Frame(self.tabs, padding=18)
        self.estratos_tab = ttk.Frame(self.tabs, padding=18)
        self.cargas_tab = ttk.Frame(self.tabs, padding=18)
        self.salida = ttk.Frame(self.tabs, padding=12)
        
        for tab, title in ((self.general, '1 · Datos generales'), (self.estratos_tab, '2 · Estratos y agua'),
                          (self.cargas_tab, '3 · Sobrecargas'), (self.salida, '4 · Resultados')):
            self.tabs.add(tab, text=title)
            
        # Llenar cada pestaña con sus campos
        self._general()
        self._estratos()
        self._cargas()
        self._salida()
        self._toggle_metodo() # Ocultar columna delta por defecto si arranca en Rankine
        
        # Integración de Matplotlib dentro de Tkinter para los gráficos
        self.fig_perfil = Figure(figsize=(10, 3.5), dpi=100, constrained_layout=True)
        self.ax_perfil = self.fig_perfil.add_subplot(111)
        self.ax_perfil.axis('off') # Apaga el plano cartesiano por defecto al arrancar
        self.canvas_perfil = FigureCanvasTkAgg(self.fig_perfil, master=self.frame_perfil)
        self.canvas_perfil.get_tk_widget().pack(fill='both', expand=True)
        
        self.fig_resul = Figure(figsize=(5, 4), dpi=100, constrained_layout=True)
        self.ax_resul = self.fig_resul.add_subplot(111)
        self.ax_resul.axis('off') # Apaga el plano cartesiano por defecto al arrancar
        self.canvas_resul = FigureCanvasTkAgg(self.fig_resul, master=self.frame_graf_resul)
        self.canvas_resul.get_tk_widget().pack(fill='both', expand=True)

    def _entry(self, parent, row, text, value, width=14):
        """Función auxiliar para crear un Label y un Entry juntos, retorna la Variable y los widgets."""
        lbl = ttk.Label(parent, text=text)
        lbl.grid(row=row, column=0, padx=6, pady=7, sticky='w')
        var = tk.StringVar(value=str(value))
        ent = ttk.Entry(parent, textvariable=var, width=width)
        ent.grid(row=row, column=1, padx=6, pady=7, sticky='w')
        return var, lbl, ent

    def _general(self):
        """Construye los elementos de la pestaña 1 (Parámetros del muro y análisis)."""
        f = ttk.LabelFrame(self.general, text='Geometría y análisis', padding=15); f.pack(anchor='nw', fill='x')
        
        # Configuración del tipo de muro
        ttk.Label(f, text='Tipo de muro').grid(row=0, column=0, sticky='w', padx=6, pady=7)
        self.tipo_muro = tk.StringVar(value='Rectangular')
        self.combo_tipo = ttk.Combobox(f, textvariable=self.tipo_muro, values=['Rectangular', 'Trapezoidal'], state='readonly', width=15)
        self.combo_tipo.grid(row=0, column=1, padx=6, sticky='w')
        self.combo_tipo.bind('<<ComboboxSelected>>', self._cambio_tipo_muro)
        
        # Opciones de personalización de geometría
        ttk.Label(f, text='Modificar dimensiones').grid(row=1, column=0, sticky='w', padx=6, pady=7)
        self.modo_muro = tk.StringVar(value='Genérico')
        combo_modo = ttk.Combobox(f, textvariable=self.modo_muro, values=['Genérico', 'Personalizado'], state='readonly', width=15)
        combo_modo.grid(row=1, column=1, padx=6, sticky='w')
        combo_modo.bind('<<ComboboxSelected>>', self._toggle_campos_muro)
        
        # Variables geométricas
        self.b_base, self.lbl_b, self.ent_b = self._entry(f, 2, 'Ancho de base B (m)', 2.0)
        self.e_pantalla, self.lbl_e, self.ent_e = self._entry(f, 3, 'Espesor pantalla (m)', 0.5)
        self.altura, self.lbl_altura, _ = self._entry(f, 4, 'Altura total H (m)', 5.00)
        self.beta, _, _ = self._entry(f, 5, 'Ángulo del muro β (°)', 90)
        self.alpha, _, _ = self._entry(f, 6, 'Ángulo del relleno α (°)', 0)
        
        # Variables de cálculo geotécnico
        ttk.Label(f, text='Condición').grid(row=7, column=0, sticky='w', padx=6, pady=7)
        self.cond = tk.StringVar(value='activa')
        ttk.Combobox(f, textvariable=self.cond, values=['activa','pasiva','reposo'], state='readonly', width=15).grid(row=7, column=1, padx=6, sticky='w')
        
        ttk.Label(f, text='Método').grid(row=8, column=0, sticky='w', padx=6, pady=7)
        self.metodo = tk.StringVar(value='Rankine')
        self.combo_metodo = ttk.Combobox(f, textvariable=self.metodo, values=['Rankine','Coulomb'], state='readonly', width=15)
        self.combo_metodo.grid(row=8, column=1, padx=6, sticky='w')
        # Si cambiamos el método, revisamos si debemos ocultar delta (Fricción muro-suelo)
        self.combo_metodo.bind('<<ComboboxSelected>>', self._toggle_metodo)
        
        # Sismo
        self.kh, _, _ = self._entry(f, 9, 'kh (0 = estático)', 0)
        self.kv, _, _ = self._entry(f, 10, 'kv (+ hacia arriba)', 0)
        
        self._toggle_campos_muro()

    def _toggle_metodo(self, event=None):
        """Muestra u oculta dinámicamente la columna Delta (δ) dependiendo si es Rankine o Coulomb."""
        cols = ['#','h (m)','γ (kN/m³)','γsat (kN/m³)','φ′ (°)','c′ (kN/m²)','δ (°)']
        if hasattr(self, 'tabla_e'):
            if self.metodo.get() == 'Rankine':
                # Omite la última columna (delta)
                self.tabla_e["displaycolumns"] = cols[:-1]
            else:
                # Muestra todas las columnas
                self.tabla_e["displaycolumns"] = cols
            self._actualizar_grafico_muro()

    def _cambio_tipo_muro(self, event=None):
        """Valida que el muro trapezoidal tenga un ángulo β lógico (< 90°)."""
        tipo = self.tipo_muro.get()
        if tipo == 'Trapezoidal':
            try:
                beta_val = float(self.beta.get().replace(',', '.'))
                if beta_val >= 90:
                    self.beta.set('45')
                    return
            except ValueError:
                self.beta.set('45')
                return
        elif tipo == 'Rectangular':
            self.beta.set('90')
            return
        self._actualizar_grafico_muro()

    def _toggle_campos_muro(self, event=None):
        """Muestra/Oculta las casillas de Base y Espesor según si es Genérico o Personalizado."""
        if self.modo_muro.get() == 'Personalizado':
            self.lbl_b.grid(row=2, column=0, sticky='w', padx=6, pady=7)
            self.ent_b.grid(row=2, column=1, padx=6, sticky='w')
            self.lbl_e.grid(row=3, column=0, sticky='w', padx=6, pady=7)
            self.ent_e.grid(row=3, column=1, padx=6, sticky='w')
        else:
            self.lbl_b.grid_forget()
            self.ent_b.grid_forget()
            self.lbl_e.grid_forget()
            self.ent_e.grid_forget()
        self._actualizar_grafico_muro()

    def _tabla(self, parent, cols, height=9):
        """Crea un widget Treeview (tabla estilo Excel) estándar para ser reutilizado."""
        f = ttk.Frame(parent); f.pack(fill='both', expand=True, pady=8)
        t = ttk.Treeview(f, columns=cols, show='headings', height=height, selectmode='browse')
        for col in cols:
            t.heading(col, text=col); t.column(col, width=110, anchor='center', stretch=True)
        s = ttk.Scrollbar(f, orient='vertical', command=t.yview); t.configure(yscroll=s.set)
        t.pack(side='left', fill='both', expand=True); s.pack(side='right', fill='y')
        return t

    def _estratos(self):
        """Construye la Pestaña 2 (Estratos y Nivel Freático)."""
        top = ttk.LabelFrame(self.estratos_tab, text='Nivel freático', padding=10); top.pack(fill='x')
        self.agua = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text='Considerar agua', variable=self.agua).grid(row=0, column=0, padx=8)
        self.nf, self.lbl_nf, _ = self._entry(top, 1, 'NF (m)', 0.0)
        self.gamma_agua, self.lbl_g_agua, _ = self._entry(top, 2, 'γagua (kN/m³)', 9.81)
        
        botones = ttk.Frame(self.estratos_tab)
        botones.pack(side='bottom', fill='x', pady=(5, 0))
        ttk.Button(botones, text='+ Agregar estrato', command=self._agregar_estrato).pack(side='left', padx=3)
        ttk.Button(botones, text='Eliminar seleccionado', command=lambda: self._eliminar(self.tabla_e)).pack(side='left', padx=3)
        ttk.Label(botones, text='(Arrastra para ordenar. Doble clic para modificar)').pack(side='left', padx=15)

        self.tabla_e = self._tabla(self.estratos_tab, ['#','h (m)','γ (kN/m³)','γsat (kN/m³)','φ′ (°)','c′ (kN/m²)','δ (°)'], height=6)
        
        # Vinculación de eventos de ratón
        self.tabla_e.bind('<Double-1>', lambda e: self._iniciar_edicion_celda(e, self.tabla_e, es_estrato=True))
        self.tabla_e.bind('<ButtonPress-1>', self._on_drag_start)
        self.tabla_e.bind('<B1-Motion>', self._on_drag_motion)
        self.tabla_e.bind('<ButtonRelease-1>', self._on_drag_release)

    def _on_drag_start(self, event):
        """Inicia el arrastre de una fila de la tabla."""
        row = self.tabla_e.identify_row(event.y)
        self.drag_data = {'item': row} if row else None

    def _on_drag_motion(self, event): pass

    def _on_drag_release(self, event):
        """Finaliza el arrastre y reordena la tabla."""
        if not getattr(self, 'drag_data', None) or not self.drag_data.get('item'): return
        target_row = self.tabla_e.identify_row(event.y)
        item = self.drag_data['item']
        if target_row and target_row != item:
            target_idx = self.tabla_e.index(target_row)
            self.tabla_e.move(item, '', target_idx)
            self._renumerar()
            self._recalcular_estratos()
        self.drag_data = None

    def _on_altura_trace(self, *args):
        """Ejecuta la redistribución de estratos si el valor de H cambia."""
        self._recalcular_estratos()

    def _recalcular_estratos(self):
        """
        Adapta la altura de los estratos al valor de H maestro.
        Mantiene 'bloqueadas' las alturas que el usuario editó explícitamente a mano,
        y divide el espacio sobrante equitativamente en el resto.
        """
        try:
            h_total = float(self.altura.get().replace(',', '.'))
        except ValueError:
            return
            
        filas = self.tabla_e.get_children()
        if not filas:
            self._actualizar_grafico_muro()
            return
            
        locked_items = []
        unlocked_items = []
        
        # Identificar qué estratos fueron bloqueados (modificados por el usuario, bandera '1' oculta en índice 7)
        for item in filas:
            vals = list(self.tabla_e.item(item, 'values'))
            if len(vals) < 8: vals.append('0')
            if vals[7] == '1': locked_items.append(item)
            else: unlocked_items.append(item)
                
        sum_locked = sum(float(self.tabla_e.item(item, 'values')[1]) for item in locked_items)
        h_remaining = h_total - sum_locked
        
        # Si la matemática rompe (ej: H menor que la suma de bloqueados), forzar desbloqueo general
        if h_remaining < 0 or (not unlocked_items and abs(h_remaining) > 1e-5):
            unlocked_items = list(filas)
            locked_items = []
            sum_locked = 0.0
            h_remaining = h_total
            for item in filas:
                vals = list(self.tabla_e.item(item, 'values'))
                if len(vals) >= 8: vals[7] = '0'
                else: vals.append('0')
                self.tabla_e.item(item, values=vals)
                
        # Repartir el resto equitativamente
        if unlocked_items:
            h_new = h_remaining / len(unlocked_items)
            for item in unlocked_items:
                vals = list(self.tabla_e.item(item, 'values'))
                vals[1] = f"{h_new:.2f}"
                self.tabla_e.item(item, values=vals)
                
        self._actualizar_grafico_muro()

    def _cargas(self):
        """Construye la Pestaña 3 (Sobrecargas superficiales)."""
        botones = ttk.Frame(self.cargas_tab)
        botones.pack(side='bottom', fill='x', pady=(5, 0))
        ttk.Button(botones, text='+ Agregar sobrecarga', command=self._agregar_carga).pack(side='left', padx=3)
        ttk.Button(botones, text='Eliminar seleccionada', command=lambda: self._eliminar(self.tabla_c)).pack(side='left', padx=3)
        ttk.Label(botones, text='(Doble clic sobre el dato para modificarlo)').pack(side='left', padx=15)

        self.tabla_c = self._tabla(self.cargas_tab, ['Tipo','Magnitud','a (m)','B (m)'], height=6)
        self.tabla_c.bind('<Double-1>', lambda e: self._iniciar_edicion_celda(e, self.tabla_c, es_estrato=False))
        self.tabla_c.bind('<<TreeviewSelect>>', lambda e: self._actualizar_grafico_muro())

    def _iniciar_edicion_celda(self, event, tree, es_estrato):
        """Habilita la edición in-situ (haciendo doble clic) simulando celdas editables."""
        region = tree.identify("region", event.x, event.y)
        if region != "cell": return
        column = tree.identify_column(event.x)
        col_idx = int(column[1:]) - 1
        
        if es_estrato and col_idx == 0: return # No permite cambiar el número "#" de fila
        item_id = tree.focus()
        if not item_id: return
        bbox = tree.bbox(item_id, column)
        if not bbox: return
        x, y, w, h = bbox
        
        if hasattr(self, '_editor_activo') and self._editor_activo.winfo_exists():
            self._editor_activo.destroy()
            
        current_value = tree.item(item_id, 'values')[col_idx]
        
        # Desplegable para el tipo de sobrecarga, Entry para todo lo demás
        if not es_estrato and col_idx == 0:
            editor = ttk.Combobox(tree, values=['uniforme', 'puntual', 'lineal', 'franja'], state='readonly')
            editor.set(current_value)
        else:
            editor = ttk.Entry(tree)
            editor.insert(0, current_value)
            editor.select_range(0, tk.END)
            
        editor.place(x=x, y=y, width=w, height=h)
        editor.focus()
        self._editor_activo = editor
        
        def guardar_edicion(evt=None):
            """Se ejecuta al presionar Enter o perder el foco."""
            if not editor.winfo_exists(): return
            nuevo_valor = editor.get()
            valores = list(tree.item(item_id, 'values'))
            
            # Validación de datos numéricos flotantes
            if es_estrato or col_idx > 0:
                try: nuevo_valor = str(float(nuevo_valor.replace(',', '.')))
                except ValueError: 
                    editor.destroy()
                    return 
                    
            valores[col_idx] = nuevo_valor
            
            # Si se edita la columna 1 ('h (m)') se bloquea esa celda (bandera en índice 7)
            if es_estrato and col_idx == 1:
                if len(valores) < 8: valores.append('1')
                else: valores[7] = '1'
                
            tree.item(item_id, values=valores)
            editor.destroy()
            
            if es_estrato:
                self._renumerar()
                if col_idx == 1: self._recalcular_estratos()
                else: self._actualizar_grafico_muro()
            else:
                self._actualizar_grafico_muro()
                
        def cancelar_edicion(evt): editor.destroy()
        editor.bind('<Return>', guardar_edicion)
        editor.bind('<FocusOut>', guardar_edicion)
        editor.bind('<Escape>', cancelar_edicion)

    def _agregar_estrato(self):
        self.tabla_e.insert('', 'end', values=[0, 0.0, 18, 20, 30, 0, 0, '0'])
        self._renumerar(); self._recalcular_estratos()

    def _agregar_carga(self):
        self.tabla_c.insert('', 'end', values=['franja', 150, 2, 2])
        self._actualizar_grafico_muro()

    def _renumerar(self):
        """Actualiza la columna '#' de las tablas tras un cambio o eliminación."""
        for j, id in enumerate(self.tabla_e.get_children(), 1):
            valores = list(self.tabla_e.item(id, 'values'))
            valores[0] = j
            self.tabla_e.item(id, values=valores)

    def _eliminar(self, tabla):
        for id in tabla.selection(): tabla.delete(id)
        if tabla is self.tabla_e: 
            self._renumerar()
            self._recalcular_estratos()
        else:
            self._actualizar_grafico_muro()

    def _salida(self):
        """Construye la Pestaña 4 (Resultados numéricos y selector de unidades)."""
        arriba = ttk.Frame(self.salida); arriba.pack(side='top', fill='x')
        self.resumen = ttk.Label(arriba, text='Calcula el caso para ver resultados.', style='Head.TLabel')
        self.resumen.pack(side='left')
        
        # Menú desplegable para transformar resultados a otra unidad visual
        lbl_uni = ttk.Label(arriba, text="  |  Mostrar en:")
        lbl_uni.pack(side='left', padx=(15, 2))
        self.cb_unidad_res = ttk.Combobox(arriba, values=['kN/m² (kPa)', 'Pa (N/m²)', 'MPa (MN/m²)', 'tonf/m²', 'kgf/cm²'], state='readonly', width=12)
        self.cb_unidad_res.set('kN/m² (kPa)')
        self.cb_unidad_res.pack(side='left')
        self.cb_unidad_res.bind('<<ComboboxSelected>>', lambda e: self._actualizar_resultados_por_unidad())

        ttk.Button(arriba, text='Exportar CSV + PNG', command=self._exportar).pack(side='right')
        
        # Tabla resumen por componentes (Suelo, Agua, Sismo...)
        self.componentes = ttk.Treeview(self.salida, columns=['Componente','P (kN/m)','M base (kN·m/m)','y base (m)'], show='headings', height=5)
        for c in self.componentes['columns']:
            self.componentes.heading(c, text=c); self.componentes.column(c, width=150, anchor='center')
        self.componentes.pack(side='top', fill='x', pady=8)
        
        self.nota = ttk.Label(self.salida, text='', wraplength=500); self.nota.pack(side='bottom', fill='x', pady=6)
        
        # Tabla desglosada profundidad a profundidad (z)
        frame_tabla = ttk.Frame(self.salida)
        frame_tabla.pack(side='top', fill='both', expand=True)
        self.tabla_r = ttk.Treeview(frame_tabla, columns=['z','Estrato','σ′v','K','Suelo','Agua','Carga','Sismo','Total'], show='headings')
        for c in self.tabla_r['columns']:
            self.tabla_r.heading(c, text=c); self.tabla_r.column(c, width=82, anchor='center')
        s = ttk.Scrollbar(frame_tabla, orient='vertical', command=self.tabla_r.yview); self.tabla_r.configure(yscroll=s.set)
        self.tabla_r.pack(side='left', fill='both', expand=True); s.pack(side='right', fill='y')

    def _obtener_factores_unidad(self):
        """Retorna las constantes matemáticas para convertir desde el sistema base al seleccionado."""
        sel = self.cb_unidad_res.get()
        # Devuelve: factor_presion, factor_fuerza, factor_momento, unidad_presion, unidad_fuerza, unidad_momento
        if sel == 'Pa (N/m²)': return 1000.0, 1000.0, 1000.0, 'Pa', 'N/m', 'N·m/m'
        if sel == 'MPa (MN/m²)': return 0.001, 0.001, 0.001, 'MPa', 'MN/m', 'MN·m/m'
        if sel == 'tonf/m²': return 1/9.80665, 1/9.80665, 1/9.80665, 'tonf/m²', 'tonf/m', 'tonf·m/m'
        if sel == 'kgf/cm²': return 1/98.0665, 1000/9.80665, 1000/9.80665, 'kgf/cm²', 'kgf/m', 'kgf·m/m'
        if sel == 'kip/ft² (ksf)': return 0.001, 0.001, 0.001, 'ksf', 'kip/ft', 'kip·ft/ft'
        if sel == 'lb/in² (psi)': return 1/144.0, 1.0, 1.0, 'psi', 'lb/ft', 'lb·ft/ft'
        if sel == 'lb/ft² (psf)': return 1.0, 1.0, 1.0, 'psf', 'lb/ft', 'lb·ft/ft'
        return 1.0, 1.0, 1.0, 'kN/m²', 'kN/m', 'kN·m/m'

    def _actualizar_resultados_por_unidad(self):
        """Reescribe las tablas y manda a repintar el gráfico multiplicando por el factor seleccionado."""
        if not self.resultado: return
        r = self.resultado
        fp, ff, fm, sp, sf, sm = self._obtener_factores_unidad()
        
        self.resumen.configure(text=f'P = {r.total * ff:.3f} {sf}    |    M = {r.momento * fm:.3f} {sm}    |    y = {r.y:.3f} m')
        
        for id in self.componentes.get_children(): self.componentes.delete(id)
        self.componentes.heading('P (kN/m)', text=f'P ({sf})')
        self.componentes.heading('M base (kN·m/m)', text=f'M base ({sm})')
        
        for nombre, vals in [*r.componentes.items(), ('TOTAL', (r.total, r.momento, r.y))]:
            self.componentes.insert('', 'end', values=[nombre, f'{vals[0]*ff:.3f}', f'{vals[1]*fm:.3f}', f'{vals[2]:.3f}'])
            
        for id in self.tabla_r.get_children(): self.tabla_r.delete(id)
        self.tabla_r.heading('σ′v', text=f'σ′v ({sp})')
        self.tabla_r.heading('Suelo', text=f'Suelo ({sp})')
        self.tabla_r.heading('Agua', text=f'Agua ({sp})')
        self.tabla_r.heading('Carga', text=f'Carga ({sp})')
        self.tabla_r.heading('Sismo', text=f'Sismo ({sp})')
        self.tabla_r.heading('Total', text=f'Total ({sp})')

        paso = max(1, len(r.filas)//500) # Evita sobrecargar la RAM visual si hay miles de rebanadas (dz)
        for a in r.filas[::paso]:
            self.tabla_r.insert('', 'end', values=[
                f'{a.z:.2f}', a.estrato, 
                f'{a.sigma_v*fp:.2f}', f'{a.k:.3f}', 
                f'{a.suelo*fp:.2f}', f'{a.agua*fp:.2f}', 
                f'{a.carga*fp:.2f}', f'{a.sismo*fp:.2f}', f'{a.total*fp:.2f}'
            ])
            
        # Pasa los factores al motor gráfico para que las etiquetas se escalen
        renderizar_presiones(self.ax_resul, r, factor_p=fp, unidad_p=sp)
        self.canvas_resul.draw_idle()

    def _float(self, var): 
        """Intenta parsear de forma segura un String de Tkinter a Float matemático."""
        try: return float(var.get().replace(',', '.'))
        except ValueError: return 0.0
        
    def _actualizar_grafico_muro(self, *args):
        """Manda toda la data bruta ingresada hasta el momento al módulo grafico.py para pintarla en vivo."""
        try:
            beta_str = self.beta.get().replace(',', '.')
            if not beta_str: return
            beta_val = float(beta_str)
            tipo_val = self.tipo_muro.get()
            
            # Chequeo lógico para muro trapezoidal (CORREGIDO: tipo_val evita el Crash NameError)
            if tipo_val == 'Trapezoidal' and beta_val >= 90:
                def corregir_angulo():
                    self.beta.set('89')
                    messagebox.showwarning("Dato inválido", "El ángulo β para un muro trapezoidal isósceles debe ser estrictamente menor a 90°.")
                self.after_idle(corregir_angulo)
                return

            h_val = self._float(self.altura)
            alpha_val = self._float(self.alpha) 
            nf_val = self._float(self.nf) if self.agua.get() else None
            modo_val = self.modo_muro.get()
            b_val = self._float(self.b_base)
            e_val = self._float(self.e_pantalla)
            
            estratos = [Estrato(*[float(x) for x in self.tabla_e.item(id,'values')[1:7]]) for id in self.tabla_e.get_children()]
            cargas_data = [self.tabla_c.item(id,'values') for id in self.tabla_c.get_children()]
            
            # Ocultar o mostrar el panel de la derecha (Diagrama de presiones) si aún no se ha calculado
            panes = [str(p) for p in self.top_pw_h.panes()]
            if self.resultado is None:
                if str(self.frame_graf_resul) in panes:
                    self.top_pw_h.forget(self.frame_graf_resul)
            else:
                if str(self.frame_graf_resul) not in panes:
                    self.top_pw_h.add(self.frame_graf_resul, weight=1)
            
            renderizar_perfil(self.ax_perfil, h_val, estratos, cargas_data, nf_val, alpha_val, beta_val, tipo_val, modo_val, b_val, e_val)
            self.canvas_perfil.draw_idle()
            
            if self.resultado is not None:
                renderizar_presiones(self.ax_resul, self.resultado)
                self.canvas_resul.draw_idle()

        except Exception:
            pass # Si falla por estar a medio tipear un número, silencia el error y no rompe el programa

    def _calcular(self):
        """Ejecución central: Extrae los datos, los envía a calculo.py y orquesta la UI con el Resultado."""
        try:
            estratos = [Estrato(*[float(x) for x in self.tabla_e.item(id,'values')[1:7]]) for id in self.tabla_e.get_children()]
            if not estratos:
                return messagebox.showerror('Faltan datos', 'Debe agregar al menos un estrato para poder calcular.')
            
            beta_str = self.beta.get().replace(',', '.')
            beta_val = float(beta_str) if beta_str else 90.0
            
            if self.tipo_muro.get() == 'Trapezoidal' and beta_val >= 90:
                self.beta.set('89')
                return messagebox.showerror('Dato inválido', 'El ángulo β para un muro trapezoidal isósceles debe ser estrictamente menor a 90°.')

            cargas = [Carga(row[0], *[float(x) for x in row[1:]]) for id in self.tabla_c.get_children() for row in [self.tabla_c.item(id,'values')]]
            
            # Ensamblar objeto 'Caso' general
            caso = Caso(self._float(self.altura), estratos, self.cond.get(), self.metodo.get(),
                      self._float(self.nf) if self.agua.get() else None, self._float(self.gamma_agua),
                      self._float(self.alpha), self._float(self.beta), self._float(self.kh), self._float(self.kv), cargas)
                      
            # Llamado al motor matemático (Integration)
            self.resultado = resolver(caso)
            
        except (ValueError, OverflowError, ZeroDivisionError) as exc:
            return messagebox.showerror('Revisar los datos', str(exc))
            
        r = self.resultado
        self.resumen.configure(text=f'P = {r.total:.3f} kN/m    |    M = {r.momento:.3f} kN·m/m    |    y = {r.y:.3f} m')
        
        # Forzar mostrar la pestaña de gráficos derechos
        panes = [str(p) for p in self.top_pw_h.panes()]
        if str(self.frame_graf_resul) not in panes:
            self.top_pw_h.add(self.frame_graf_resul, weight=1)
            
        cargas_data = [self.tabla_c.item(id,'values') for id in self.tabla_c.get_children()]
        renderizar_perfil(self.ax_perfil, self._float(self.altura), estratos, cargas_data, self._float(self.nf) if self.agua.get() else None, self._float(self.alpha), self._float(self.beta), self.tipo_muro.get(), self.modo_muro.get(), self._float(self.b_base), self._float(self.e_pantalla))
        self.canvas_perfil.draw()
        
        self.nota.configure(text='  '.join(r.notas))
        self.tabs.select(self.salida)
        
        # Pinta la tabla y el gráfico utilizando la unidad que esté seleccionada
        self._actualizar_resultados_por_unidad()

    def _exportar(self):
        """Llama al módulo exportar.py para generar un archivo Excel (CSV) y captura la gráfica en PNG."""
        if self.resultado is None: return messagebox.showinfo('Exportación', 'Primero calcule el caso.')
        path = filedialog.asksaveasfilename(title='Nombre base para CSV y PNG', defaultextension='.csv', filetypes=[('CSV','*.csv')])
        if path:
            try:
                archivos = exportar(self.resultado, path)
                png_path = path.replace('.csv', '.png')
                self.fig_resul.savefig(png_path, dpi=200, bbox_inches='tight') # Captura de Matplotlib
                archivos.append(png_path)
                messagebox.showinfo('Archivos guardados', '\n'.join(map(str, archivos)))
            except OSError as exc: messagebox.showerror('No se pudo guardar', str(exc))

    def _limpiar(self):
        """Reinicia la aplicación a su estado base de apertura."""
        self.tipo_muro.set('Rectangular')
        self.modo_muro.set('Genérico')
        self._toggle_campos_muro()
        
        for v, x in ((self.altura, 5.0), (self.beta, 90), (self.alpha, 0), (self.kh, 0), (self.kv, 0), (self.nf, 0), (self.gamma_agua, 9.81), (self.b_base, 2.0), (self.e_pantalla, 0.5)):
            v.set(str(x))
        self.cond.set('activa')
        self.metodo.set('Rankine')
        self._toggle_metodo()
        self.agua.set(False)  
        
        for t in (self.tabla_e, self.tabla_c):
            for id in t.get_children(): t.delete(id)
            
        self.resultado = None
        self._recalcular_estratos()
        self.tabs.select(self.general)

    def _guardar_proyecto(self):
        """Empaqueta todos los datos en un diccionario y los serializa a formato JSON para guardar estado."""
        datos = {
            "general": {
                "tipo_muro": self.tipo_muro.get(), "modo_muro": self.modo_muro.get(),
                "b_base": self.b_base.get(), "e_pantalla": self.e_pantalla.get(),
                "altura": self.altura.get(), "beta": self.beta.get(), "alpha": self.alpha.get(),
                "cond": self.cond.get(), "metodo": self.metodo.get(),
                "kh": self.kh.get(), "kv": self.kv.get()
            },
            "agua": { "considerar": self.agua.get(), "nf": self.nf.get(), "gamma_agua": self.gamma_agua.get() },
            "estratos": [self.tabla_e.item(id, 'values') for id in self.tabla_e.get_children()],
            "cargas": [self.tabla_c.item(id, 'values') for id in self.tabla_c.get_children()]
        }
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Archivos JSON", "*.json")])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(datos, f, indent=4)
                
    def _abrir_proyecto(self):
        """Deserializa el archivo JSON y distribuye la data en todos los Entrys y Treeviews."""
        path = filedialog.askopenfilename(filetypes=[("Archivos JSON", "*.json")])
        if path:
            with open(path, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            
            gen = datos.get("general", {})
            self.tipo_muro.set(gen.get("tipo_muro", "Rectangular"))
            self.modo_muro.set(gen.get("modo_muro", "Genérico"))
            self.b_base.set(gen.get("b_base", "2.0"))
            self.e_pantalla.set(gen.get("e_pantalla", "0.5"))
            self.altura.set(gen.get("altura", "5.00"))
            self.beta.set(gen.get("beta", "90"))
            self.alpha.set(gen.get("alpha", "0"))
            self.cond.set(gen.get("cond", "activa"))
            self.metodo.set(gen.get("metodo", "Rankine"))
            self._toggle_metodo()
            self.kh.set(gen.get("kh", "0"))
            self.kv.set(gen.get("kv", "0"))
            
            ag = datos.get("agua", {})
            self.agua.set(ag.get("considerar", False))
            self.nf.set(ag.get("nf", "0.0"))
            self.gamma_agua.set(ag.get("gamma_agua", "9.81"))
            
            for id in self.tabla_e.get_children(): self.tabla_e.delete(id)
            for est in datos.get("estratos", []): 
                vals = list(est)
                if len(vals) < 8: vals.append('0')
                self.tabla_e.insert('', 'end', values=vals)
                
            for id in self.tabla_c.get_children(): self.tabla_c.delete(id)
            for car in datos.get("cargas", []): self.tabla_c.insert('', 'end', values=car)
                
            self.resultado = None
            self._recalcular_estratos()

    def _config_unidades(self):
        """Abre un cuadro de diálogo para cambiar entre el Sistema Internacional y el Imperial globalmente."""
        dlg = tk.Toplevel(self)
        dlg.title("Configuración de unidades")
        dlg.geometry("350x180")
        dlg.transient(self) # Para que dependa de la ventana principal
        dlg.grab_set()      # Evita tocar la ventana de fondo mientras esté abierto
        
        ttk.Label(dlg, text="Seleccione el sistema de unidades visuales:", font=('Segoe UI', 10, 'bold')).pack(pady=10)
        var_unidades = tk.StringVar(value=self.sistema_unidades)
        
        ttk.Radiobutton(dlg, text="Sistema Internacional (SI) - kN, m", variable=var_unidades, value='SI').pack(anchor='w', padx=20, pady=2)
        ttk.Radiobutton(dlg, text="Sistema Imperial - lb, ft", variable=var_unidades, value='Imperial').pack(anchor='w', padx=20, pady=2)
        
        def guardar():
            self.sistema_unidades = var_unidades.get()
            self._actualizar_textos_unidades()
            dlg.destroy()
            
        ttk.Button(dlg, text="Aplicar cambios", command=guardar).pack(pady=15)
        
    def _actualizar_textos_unidades(self):
        """Actualiza todos los textos estáticos de la interfaz a la unidad elegida (SI/Imperial)."""
        if self.sistema_unidades == 'SI':
            self.lbl_unidades_sub.config(text='Unidades SI · resultados horizontales por metro de muro')
            self.lbl_b.config(text='Ancho de base B (m)')
            self.lbl_e.config(text='Espesor pantalla (m)')
            self.lbl_altura.config(text='Altura total H (m)')
            self.lbl_nf.config(text='NF (m)')
            self.lbl_g_agua.config(text='γagua (kN/m³)')
            self.tabla_e.heading('h (m)', text='h (m)')
            self.tabla_e.heading('γ (kN/m³)', text='γ (kN/m³)')
            self.tabla_e.heading('γsat (kN/m³)', text='γsat (kN/m³)')
            self.tabla_e.heading('c′ (kN/m²)', text='c′ (kN/m²)')
            self.tabla_c.heading('a (m)', text='a (m)')
            self.tabla_c.heading('B (m)', text='B (m)')
            self.cb_unidad_res['values'] = ['kN/m² (kPa)', 'Pa (N/m²)', 'MPa (MN/m²)', 'tonf/m²', 'kgf/cm²']
            self.cb_unidad_res.set('kN/m² (kPa)')
        else:
            self.lbl_unidades_sub.config(text='Unidades Imperiales · resultados por pie de muro')
            self.lbl_b.config(text='Ancho de base B (ft)')
            self.lbl_e.config(text='Espesor pantalla (ft)')
            self.lbl_altura.config(text='Altura total H (ft)')
            self.lbl_nf.config(text='NF (ft)')
            self.lbl_g_agua.config(text='γagua (pcf)')
            self.tabla_e.heading('h (m)', text='h (ft)')
            self.tabla_e.heading('γ (kN/m³)', text='γ (pcf)')
            self.tabla_e.heading('γsat (kN/m³)', text='γsat (pcf)')
            self.tabla_e.heading('c′ (kN/m²)', text='c′ (psf)')
            self.tabla_c.heading('a (m)', text='a (ft)')
            self.tabla_c.heading('B (m)', text='B (ft)')
            self.cb_unidad_res['values'] = ['lb/ft² (psf)', 'kip/ft² (ksf)', 'lb/in² (psi)']
            self.cb_unidad_res.set('lb/ft² (psf)')
        self._actualizar_resultados_por_unidad()

# Comando de arranque del programa. 
# Solo se ejecuta si Python corre directamente este archivo.
if __name__ == '__main__':
    app = Aplicacion()
    app.mainloop()