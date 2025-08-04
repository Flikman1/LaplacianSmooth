import sys
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
import pyvista as pv
from pyvistaqt import QtInteractor


class LaplacianSmoothingApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.original_mesh = None
        self.smoothed_mesh = None
        self.orig_actor = None
        self.smooth_actor = None
        self.showing = None

        # Main window setup
        self.setWindowTitle("Laplacian Mesh Smoothing - Sci-Fi Interface")
        self.resize(1000, 600)
        # Set dark sci-fi theme (Fusion style with custom palette)
        self._set_dark_theme()

        # Central widget and layout with splitter
        central = QtWidgets.QWidget(self)
        h_layout = QtWidgets.QHBoxLayout(central)
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        h_layout.addWidget(self.splitter)
        central.setLayout(h_layout)
        self.setCentralWidget(central)

        # Left panel for controls
        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)

        # Load model button
        self.load_button = QtWidgets.QPushButton("Load 3D Model")
        left_layout.addWidget(self.load_button)
        self.load_button.clicked.connect(self.load_model)

        # Smoothing parameters group
        param_group = QtWidgets.QGroupBox("Smoothing Parameters")
        param_layout = QtWidgets.QFormLayout(param_group)
        # Lambda (smoothing factor) slider + spinbox
        self.lambda_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.lambda_slider.setRange(0, 100)    # 0 to 100 -> 0.00 to 1.00
        self.lambda_slider.setValue(50)
        self.lambda_slider.setEnabled(False)
        self.lambda_spin = QtWidgets.QDoubleSpinBox()
        self.lambda_spin.setRange(0.0, 1.0)
        self.lambda_spin.setSingleStep(0.01)
        self.lambda_spin.setValue(0.5)
        self.lambda_spin.setDecimals(2)
        self.lambda_spin.setEnabled(False)
        # Link slider and spinbox
        self.lambda_slider.valueChanged.connect(lambda val: self.lambda_spin.setValue(val/100.0))
        self.lambda_spin.valueChanged.connect(lambda val: self.lambda_slider.setValue(int(val*100)))
        # Add to layout
        lambda_row = QtWidgets.QHBoxLayout()
        lambda_row.addWidget(self.lambda_slider)
        lambda_row.addWidget(self.lambda_spin)
        param_layout.addRow("Smoothing Factor (λ):", lambda_row)
        # Iterations slider + spinbox
        self.iter_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.iter_slider.setRange(1, 50)
        self.iter_slider.setValue(10)
        self.iter_slider.setEnabled(False)
        self.iter_spin = QtWidgets.QSpinBox()
        self.iter_spin.setRange(1, 50)
        self.iter_spin.setValue(10)
        self.iter_spin.setEnabled(False)
        # Link slider and spinbox
        self.iter_slider.valueChanged.connect(self.iter_spin.setValue)
        self.iter_spin.valueChanged.connect(self.iter_slider.setValue)
        # Add to layout
        iter_row = QtWidgets.QHBoxLayout()
        iter_row.addWidget(self.iter_slider)
        iter_row.addWidget(self.iter_spin)
        param_layout.addRow("Iterations:", iter_row)
        left_layout.addWidget(param_group)

        # Apply smoothing button
        self.apply_button = QtWidgets.QPushButton("Apply Smoothing")
        self.apply_button.setEnabled(False)
        left_layout.addWidget(self.apply_button)
        self.apply_button.clicked.connect(self.apply_smoothing)

        # Preview dropdown (Original/Smoothed)
        preview_layout = QtWidgets.QHBoxLayout()
        preview_label = QtWidgets.QLabel("Preview:")
        self.preview_combo = QtWidgets.QComboBox()
        self.preview_combo.addItems(["Original Model", "Smoothed Model"])
        self.preview_combo.setEnabled(False)
        preview_layout.addWidget(preview_label)
        preview_layout.addWidget(self.preview_combo)
        left_layout.addLayout(preview_layout)
        self.preview_combo.currentIndexChanged.connect(self.update_view)

        # Save result button
        self.save_button = QtWidgets.QPushButton("Save Result")
        self.save_button.setEnabled(False)
        left_layout.addWidget(self.save_button)
        self.save_button.clicked.connect(self.save_result)

        left_layout.addStretch(1)  # push UI elements to top
        left_panel.setLayout(left_layout)

        # Right panel for 3D view
        view_frame = QtWidgets.QFrame()
        view_layout = QtWidgets.QVBoxLayout(view_frame)
        self.plotter = QtInteractor(view_frame)  # PyVista 3D render widget
        view_layout.addWidget(self.plotter.interactor)
        view_frame.setLayout(view_layout)

        # Add panels to splitter and configure layout stretch
        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(view_frame)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([300, 700])  # initial sizes

    def _set_dark_theme(self):
        """Apply a dark theme with sci-fi colors (neon highlights)."""
        app = QtWidgets.QApplication.instance()
        if app is None:
            return
        app.setStyle("Fusion")
        palette = QtGui.QPalette()
        # Dark background colors
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(20, 20, 30))
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(30, 30, 40))
        palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(20, 20, 30))
        # Text colors
        palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
        palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
        palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
        # Button background
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor(70, 70, 90))
        # Highlight color for selections/sliders (neon cyan)
        palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(0, 255, 200))
        palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
        app.setPalette(palette)
        # Set a monospaced or futuristic font if available
        font_family = "Consolas" if "Consolas" in QtGui.QFontDatabase().families() else app.font().family()
        app.setFont(QtGui.QFont(font_family, 10))

    def load_model(self):
        """Load an OBJ file and display it in the 3D viewer."""
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open 3D Model", "",
                                                        "Wavefront OBJ Files (*.obj);;All Files (*)")
        if not fname:
            return  # dialog cancelled
        try:
            mesh = pv.read(fname)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to load OBJ file:\n{e}")
            return
        # If not PolyData (e.g. an OBJ with NURBS), extract surface triangle mesh
        if not isinstance(mesh, pv.PolyData):
            mesh = mesh.extract_surface()
        self.original_mesh = mesh
        self.smoothed_mesh = None
        # Remove any existing actors from previous model
        if self.orig_actor:
            try:
                self.plotter.remove_actor(self.orig_actor)
            except:
                pass
        if self.smooth_actor:
            try:
                self.plotter.remove_actor(self.smooth_actor)
            except:
                pass
        # Add the original mesh to the scene
        self.orig_actor = self.plotter.add_mesh(self.original_mesh, color="white", smooth_shading=True)
        self.smooth_actor = None
        self.plotter.set_background("black")
        self.plotter.reset_camera()
        self.showing = 'orig'
        # Enable controls for smoothing now that a model is loaded
        self.lambda_slider.setEnabled(True)
        self.lambda_spin.setEnabled(True)
        self.iter_slider.setEnabled(True)
        self.iter_spin.setEnabled(True)
        self.apply_button.setEnabled(True)
        self.preview_combo.setEnabled(False)  # no smoothed model yet
        self.preview_combo.setCurrentIndex(0)
        self.save_button.setEnabled(False)

    def apply_smoothing(self):
        """Run Laplacian smoothing on the loaded mesh using the chosen parameters."""
        if self.original_mesh is None:
            return
        λ = self.lambda_slider.value() / 100.0  # smoothing factor 0-1
        iterations = self.iter_slider.value()
        # Perform Laplacian smoothing (keep boundaries fixed)
        new_points = self._laplacian_smooth(self.original_mesh.points, self.original_mesh.faces, λ, iterations)
        # Create a new mesh for the smoothed result
        self.smoothed_mesh = pv.PolyData(np.array(new_points), np.array(self.original_mesh.faces))
        # Remove old actors and display smoothed mesh
        if self.orig_actor:
            try:
                self.plotter.remove_actor(self.orig_actor)
            except:
                pass
            self.orig_actor = None
        if self.smooth_actor:
            try:
                self.plotter.remove_actor(self.smooth_actor)
            except:
                pass
        self.smooth_actor = self.plotter.add_mesh(self.smoothed_mesh, color="white", smooth_shading=True)
        self.showing = 'smooth'
        # Enable preview toggle and saving
        self.preview_combo.setEnabled(True)
        self.preview_combo.setCurrentIndex(1)  # switch view to Smoothed model
        self.save_button.setEnabled(True)

    def update_view(self, index):
        """Switch between original and smoothed model in the 3D view."""
        if self.original_mesh is None:
            return
        if index == 0 and self.showing != 'orig':  # show Original
            if self.smooth_actor:
                try:
                    self.plotter.remove_actor(self.smooth_actor)
                except:
                    pass
            self.orig_actor = self.plotter.add_mesh(self.original_mesh, color="white", smooth_shading=True)
            self.showing = 'orig'
        elif index == 1 and self.showing != 'smooth':  # show Smoothed
            if self.smoothed_mesh is None:
                # No smoothed mesh available, revert to original
                self.preview_combo.setCurrentIndex(0)
                return
            if self.orig_actor:
                try:
                    self.plotter.remove_actor(self.orig_actor)
                except:
                    pass
            self.smooth_actor = self.plotter.add_mesh(self.smoothed_mesh, color="white", smooth_shading=True)
            self.showing = 'smooth'

    def save_result(self):
        """Save the smoothed mesh to an OBJ file."""
        if self.smoothed_mesh is None:
            return
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Smoothed Model", "",
                                                        "Wavefront OBJ Files (*.obj)")
        if not fname:
            return
        if not fname.lower().endswith(".obj"):
            fname += ".obj"
        try:
            self.smoothed_mesh.save(fname)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save OBJ:\n{e}")

    def _laplacian_smooth(self, points, faces_arr, lambd, iterations):
        """Compute Laplacian smoothing on a set of points with given face connectivity."""
        # Convert faces from PyVista format (flat array) to list of index lists
        faces = []
        arr = np.array(faces_arr)
        i = 0
        while i < len(arr):
            n = arr[i]
            faces.append(arr[i+1 : i+1+n])
            i += 1 + n
        points = np.array(points)  # copy to NumPy array
        N = len(points)
        # Build adjacency list and find boundary vertices
        adj = {v: set() for v in range(N)}
        edge_count = {}
        for face in faces:
            face = list(face)
            m = len(face)
            for j in range(m):
                v1 = int(face[j])
                v2 = int(face[(j+1) % m])
                if v1 == v2:
                    continue
                e = tuple(sorted((v1, v2)))
                edge_count[e] = edge_count.get(e, 0) + 1
        for (u, v), count in edge_count.items():
            # Add neighbors (undirected edge)
            adj[u].add(v)
            adj[v].add(u)
        # Boundary vertices = those with any edge used only once
        boundary_verts = {u for (u, v), cnt in edge_count.items() if cnt == 1 for u in (u, v)}
        # Iteratively smooth interior vertices
        new_pts = points.copy()
        for _ in range(iterations):
            temp = new_pts.copy()
            for idx in range(N):
                if idx in boundary_verts or len(adj[idx]) == 0:
                    continue  # skip fixed boundary or isolated vertices
                # move towards average of neighbors
                nbr_indices = list(adj[idx])
                nbr_avg = np.mean(new_pts[nbr_indices], axis=0)
                temp[idx] = new_pts[idx] + lambd * (nbr_avg - new_pts[idx])
            new_pts = temp
        return new_pts

# Run the application (if this script is executed directly)
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = LaplacianSmoothingApp()
    window.show()
    sys.exit(app.exec_())
