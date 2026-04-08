#!/usr/bin/env python3
"""
Suminagashi Marbling Simulator
Interactive GUI for creating Japanese water marbling art with realistic physics
"""

import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QSlider, 
                             QColorDialog, QGroupBox, QGridLayout, QComboBox,
                             QCheckBox, QSpinBox, QDoubleSpinBox)
from PyQt5.QtCore import Qt, QTimer, QPoint, QPointF, QElapsedTimer
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen
import colorsys


class InkParticle:
    """Represents a single particle of ink spreading on water surface"""
    def __init__(self, x, y, color, strength, particle_type='ink'):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.color = color
        self.strength = strength  # Initial strength/opacity
        self.age = 0
        self.radius = 0.5
        self.particle_type = particle_type  # 'ink' or 'surfactant'
        
    def update(self, dt=1.0):
        """Update particle position and physics"""
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.age += dt
        # Slow down over time (friction)
        self.vx *= 0.98
        self.vy *= 0.98


class InkRing:
    """Represents an expanding ring of ink or surfactant"""
    def __init__(self, x, y, color, strength, ring_type='ink'):
        self.x = x
        self.y = y
        self.vx = 0  # Velocity for ring center movement
        self.vy = 0
        self.color = color
        self.strength = strength
        self.radius = 0.1
        self.max_radius = 200
        self.expansion_rate = 1.0
        self.ring_type = ring_type
        self.active = True
        self.opacity = 1.0
        self.age = 0  # Track age in frames
        
        # Distortion points around the ring
        self.num_points = 48  # More points for smoother deformation
        self.distortion_points = []
        self.initialize_distortion()
        
    def initialize_distortion(self):
        """Initialize distortion points around the ring"""
        for i in range(self.num_points):
            angle = (i / self.num_points) * 2 * np.pi
            self.distortion_points.append({
                'angle': angle,
                'offset': 0.0,      # Radial offset from base radius
                'velocity': 0.0     # Velocity of this point
            })
        
    def update(self, expansion_speed, randomness):
        """Expand the ring and update position"""
        # Add some randomness to expansion
        random_factor = 1.0 + (np.random.random() - 0.5) * randomness
        self.radius += self.expansion_rate * expansion_speed * random_factor
        
        # Update position based on velocity (from interactions)
        self.x += self.vx
        self.y += self.vy
        
        # Apply friction to velocity
        self.vx *= 0.92
        self.vy *= 0.92
        
        # Update distortion points with spring physics
        for point in self.distortion_points:
            # Spring force pulls back toward circular (0 offset)
            spring_force = -point['offset'] * 0.15
            point['velocity'] += spring_force
            # Damping
            point['velocity'] *= 0.85
            # Update position
            point['offset'] += point['velocity']
        
        # Fade out as it expands
        self.opacity = max(0, 1.0 - (self.radius / self.max_radius))
        
        self.age += 1
        
        if self.radius >= self.max_radius:
            self.active = False
            
    def apply_force(self, fx, fy):
        """Apply a force to this ring's center"""
        self.vx += fx
        self.vy += fy
        
    def apply_local_deformation(self, angle, strength):
        """Apply a localized deformation at a specific angle"""
        # Find nearby points and deform them
        for point in self.distortion_points:
            # Calculate angular distance (wrapping around)
            angle_diff = abs(point['angle'] - angle)
            if angle_diff > np.pi:
                angle_diff = 2 * np.pi - angle_diff
            
            # Deformation falls off with distance from the impact point
            # Use a Gaussian-like falloff
            influence = np.exp(-(angle_diff ** 2) / 0.5)
            
            # Apply velocity to this point
            point['velocity'] += strength * influence
            
    def get_point_position(self, index):
        """Get the actual x,y position of a distortion point"""
        point = self.distortion_points[index]
        r = self.radius + point['offset']
        x = self.x + r * np.cos(point['angle'])
        y = self.y + r * np.sin(point['angle'])
        return x, y


class SuminagashiCanvas(QWidget):
    """Main canvas for marbling simulation"""
    
    def __init__(self, width=800, height=600):
        super().__init__()
        self.canvas_width = width
        self.canvas_height = height
        self.setMinimumSize(width, height)
        
        # Create image buffer
        self.image = QImage(width, height, QImage.Format_RGB32)
        self.image.fill(QColor(240, 240, 245))  # Light water color
        
        # Simulation state
        self.ink_rings = []
        self.particles = []
        
        # Current brush settings
        self.brush_color = QColor(0, 0, 0)
        self.brush_size = 30
        self.ink_amount = 50
        
        # Physics parameters
        self.expansion_speed = 1.5
        self.randomness = 0.1
        self.surface_tension = 0.5
        self.turbulence = 0.2
        self.ring_thickness = 3.0
        self.fade_rate = 0.95
        self.interaction_strength = 1.0  # Multiplier for ring interactions
        
        # Interaction state
        self.is_touching = False
        self.touch_start_time = 0
        self.current_button = None  # Track which button is pressed
        self.elapsed_timer = QElapsedTimer()  # Track hold duration
        
        # Animation timer
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.update_physics)
        self.anim_timer.start(30)  # ~33 FPS
        
        self.setMouseTracking(True)
        self.mouse_pos = None
        
    def set_brush_color(self, color):
        """Set the current brush ink color"""
        self.brush_color = color
        
    def set_brush_size(self, size):
        """Set brush contact size"""
        self.brush_size = size
        
    def set_ink_amount(self, amount):
        """Set ink concentration (0-100)"""
        self.ink_amount = amount
        

    def set_expansion_speed(self, speed):
        """Set how fast rings expand"""
        self.expansion_speed = speed
        
    def set_randomness(self, randomness):
        """Set randomness in expansion"""
        self.randomness = randomness
        
    def set_surface_tension(self, tension):
        """Set water surface tension effect"""
        self.surface_tension = tension
        
    def set_turbulence(self, turbulence):
        """Set turbulence/chaos in spreading"""
        self.turbulence = turbulence
        
    def set_ring_thickness(self, thickness):
        """Set visible ring thickness"""
        self.ring_thickness = thickness
        
    def set_interaction_strength(self, strength):
        """Set strength of ring-to-ring interactions"""
        self.interaction_strength = strength
        
    def mousePressEvent(self, event):
        """Handle mouse press - start dipping brush"""
        if event.button() in (Qt.LeftButton, Qt.RightButton):
            self.is_touching = True
            self.current_button = event.button()
            self.mouse_pos = event.pos()
            self.elapsed_timer.start()
            
    def mouseReleaseEvent(self, event):
        """Handle mouse release - create ink or surfactant ring based on hold duration"""
        if event.button() in (Qt.LeftButton, Qt.RightButton) and self.is_touching:
            # Calculate how long the button was held
            hold_duration = self.elapsed_timer.elapsed()  # in milliseconds
            
            # Determine if this is ink (left) or surfactant (right)
            is_surfactant = (event.button() == Qt.RightButton)
            
            # Create the ring
            if self.mouse_pos:
                # Scale strength based on hold duration (50ms to 500ms range)
                duration_factor = min(hold_duration / 500.0, 1.0)
                strength = (self.ink_amount / 100.0) * (0.3 + 0.7 * duration_factor)
                
                ring_type = 'surfactant' if is_surfactant else 'ink'
                
                # Create primary ring
                ring = InkRing(
                    self.mouse_pos.x(),
                    self.mouse_pos.y(),
                    self.brush_color,
                    strength,
                    ring_type
                )
                # Max radius scales with hold duration
                ring.max_radius = self.brush_size * 3 + strength * 100 + (hold_duration / 5.0)
                self.ink_rings.append(ring)
                
                # Add turbulence particles
                if self.turbulence > 0.01:
                    num_particles = int(20 * self.turbulence * duration_factor)
                    for _ in range(num_particles):
                        angle = np.random.random() * 2 * np.pi
                        speed = np.random.random() * self.turbulence * 2
                        particle = InkParticle(
                            self.mouse_pos.x(),
                            self.mouse_pos.y(),
                            self.brush_color,
                            strength * 0.5,
                            ring_type
                        )
                        particle.vx = np.cos(angle) * speed
                        particle.vy = np.sin(angle) * speed
                        self.particles.append(particle)
            
            self.is_touching = False
            self.current_button = None
            
    def mouseMoveEvent(self, event):
        """Track mouse position for brush preview"""
        self.mouse_pos = event.pos()
        self.update()
        

    def update_physics(self):
        """Update all physics and render"""
        # Update particles
        for particle in self.particles[:]:
            particle.update()
            # Remove old particles
            if particle.age > 200 or \
               particle.x < 0 or particle.x >= self.canvas_width or \
               particle.y < 0 or particle.y >= self.canvas_height:
                self.particles.remove(particle)
        
        # Calculate ring-to-ring interactions
        self.calculate_ring_interactions()
        
        # Update rings
        active_rings = []
        for ring in self.ink_rings:
            ring.update(self.expansion_speed, self.randomness)
            if ring.active:
                active_rings.append(ring)
            else:
                # Draw final ring to permanent image before removing
                self.draw_ring_to_image(ring)
        
        self.ink_rings = active_rings
        
        self.update()
        
    def calculate_ring_interactions(self):
        """Calculate interactions between all rings based on their spatial relationship"""
        num_rings = len(self.ink_rings)
        
        for i in range(num_rings):
            ring_a = self.ink_rings[i]
            
            for j in range(i + 1, num_rings):
                ring_b = self.ink_rings[j]
                
                # Calculate distance between ring centers
                dx = ring_b.x - ring_a.x
                dy = ring_b.y - ring_a.y
                distance = np.sqrt(dx * dx + dy * dy)
                
                if distance < 1.0:
                    distance = 1.0
                
                # Determine spatial relationship between rings
                relationship = self.determine_ring_relationship(ring_a, ring_b, distance)
                
                if relationship != 'no_interaction':
                    # Calculate angles for deformation
                    angle_a_to_b = np.arctan2(dy, dx)
                    angle_b_to_a = np.arctan2(-dy, -dx)
                    
                    # Apply interactions based on relationship
                    self.apply_ring_interaction(ring_a, ring_b, relationship, 
                                               angle_a_to_b, angle_b_to_a, distance)
    
    def determine_ring_relationship(self, ring_a, ring_b, distance):
        """
        Determine how two rings are positioned relative to each other:
        - 'b_inside_a': Ring B is completely inside Ring A
        - 'a_inside_b': Ring A is completely inside Ring B
        - 'band_intersection': Rings overlap/intersect (their bands cross)
        - 'no_interaction': Too far apart
        """
        # Ring A boundaries
        a_inner = max(0, ring_a.radius - self.ring_thickness)
        a_outer = ring_a.radius + self.ring_thickness
        
        # Ring B boundaries
        b_inner = max(0, ring_b.radius - self.ring_thickness)
        b_outer = ring_b.radius + self.ring_thickness
        
        # Check if B's center is inside A's band
        if distance < a_outer and distance > a_inner:
            # B's center is in A's band - they will interact
            return 'band_intersection'
        
        # Check if B is completely inside A
        if distance + b_outer < a_inner:
            return 'b_inside_a'
        
        # Check if A is completely inside B
        if distance + a_outer < b_inner:
            return 'a_inside_b'
        
        # Check if bands are close enough to interact
        edge_distance = distance - ring_a.radius - ring_b.radius
        if abs(edge_distance) < self.ring_thickness * 3:
            return 'band_intersection'
        
        return 'no_interaction'
    
    def apply_ring_interaction(self, ring_a, ring_b, relationship, 
                               angle_a_to_b, angle_b_to_a, distance):
        """Apply forces and deformations based on ring relationship"""
        
        # Get interaction type based on ring types
        both_ink = (ring_a.ring_type == 'ink' and ring_b.ring_type == 'ink')
        has_surfactant = (ring_a.ring_type == 'surfactant' or ring_b.ring_type == 'surfactant')
        
        if relationship == 'b_inside_a':
            # Ring B is inside Ring A - deform A from the inside
            # No center repulsion - B stays inside
            
            if has_surfactant:
                # Surfactant pushes from inside - negative deformation on A's inner edge
                deform_strength = -4.0 * self.interaction_strength
            else:
                # Ink merges from inside - positive deformation
                deform_strength = 2.5 * self.interaction_strength
            
            # Deform A at the angle where B is
            ring_a.apply_local_deformation(angle_a_to_b, deform_strength)
            
        elif relationship == 'a_inside_b':
            # Ring A is inside Ring B - deform B from the inside
            
            if has_surfactant:
                # Surfactant pushes from inside
                deform_strength = -4.0 * self.interaction_strength
            else:
                # Ink merges from inside
                deform_strength = 2.5 * self.interaction_strength
            
            # Deform B at the angle where A is
            ring_b.apply_local_deformation(angle_b_to_a, deform_strength)
            
        elif relationship == 'band_intersection':
            # Rings are intersecting or very close - complex interaction
            
            # Calculate how much they overlap
            overlap = (ring_a.radius + ring_b.radius) - distance
            overlap_factor = max(0, min(overlap / (self.ring_thickness * 2), 1.0))
            
            if has_surfactant:
                # Surfactant causes repulsion
                # Push centers apart
                force = overlap_factor * 0.5 * self.interaction_strength
                dx_norm = (ring_b.x - ring_a.x) / distance
                dy_norm = (ring_b.y - ring_a.y) / distance
                ring_b.apply_force(dx_norm * force, dy_norm * force)
                ring_a.apply_force(-dx_norm * force, -dy_norm * force)
                
                # Create dents where they meet
                deform_strength = -3.0 * overlap_factor * self.interaction_strength
                ring_a.apply_local_deformation(angle_a_to_b, deform_strength)
                ring_b.apply_local_deformation(angle_b_to_a, deform_strength)
                
            else:
                # Both ink - merge together
                # Minimal center movement
                force = overlap_factor * 0.1 * self.interaction_strength
                dx_norm = (ring_b.x - ring_a.x) / distance
                dy_norm = (ring_b.y - ring_a.y) / distance
                ring_b.apply_force(dx_norm * force, dy_norm * force)
                ring_a.apply_force(-dx_norm * force, -dy_norm * force)
                
                # Deform outward where they meet - flowing together
                deform_strength = 3.5 * overlap_factor * self.interaction_strength
                ring_a.apply_local_deformation(angle_a_to_b, deform_strength)
                ring_b.apply_local_deformation(angle_b_to_a, deform_strength)
                        
    def calculate_interaction_force(self, ring_a, ring_b, edge_distance, center_distance):
        """Calculate the force magnitude between two rings"""
        
        # Determine interaction type and strength
        if ring_a.ring_type == 'surfactant' or ring_b.ring_type == 'surfactant':
            # Surfactant interactions are stronger
            base_strength = 2.0
        else:
            # Ink-to-ink interactions are weaker
            base_strength = 0.8
        
        # Force decreases with distance
        if edge_distance < 0:
            # Rings are overlapping - strong repulsion
            force = -edge_distance * 0.5 * base_strength
        else:
            # Rings are close but not touching - weaker repulsion
            force = (30 - edge_distance) / 30.0 * 0.3 * base_strength
        
        # Scale by ring strengths and interaction parameter
        combined_strength = (ring_a.strength + ring_b.strength) / 2.0
        force *= combined_strength * self.interaction_strength
        
        return force
        
    def draw_ring_to_image(self, ring):
        """Draw a ring permanently to the image buffer"""
        painter = QPainter(self.image)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate color with opacity
        color = QColor(ring.color)
        
        if ring.ring_type == 'surfactant':
            # Surfactant pushes ink away, creating lighter rings
            opacity = int(255 * ring.strength * ring.opacity * 0.3)
            color = QColor(255, 255, 255, opacity)
        else:
            opacity = int(255 * ring.strength * ring.opacity)
            color.setAlpha(opacity)
        
        # Draw ring with thickness
        pen = QPen(color)
        pen.setWidthF(self.ring_thickness)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        
        # Check if ring is significantly deformed
        max_offset = max(abs(p['offset']) for p in ring.distortion_points)
        
        if max_offset > 1.0:
            # Draw as deformed polygon
            from PyQt5.QtGui import QPainterPath
            path = QPainterPath()
            
            # Start at first point
            x0, y0 = ring.get_point_position(0)
            path.moveTo(x0, y0)
            
            # Draw smooth curve through all points
            for i in range(1, ring.num_points + 1):
                idx = i % ring.num_points
                x, y = ring.get_point_position(idx)
                path.lineTo(x, y)
            
            painter.drawPath(path)
        else:
            # Draw as simple circle
            painter.drawEllipse(
                QPointF(ring.x, ring.y),
                ring.radius,
                ring.radius
            )
        
        painter.end()
        
    def paintEvent(self, event):
        """Render the canvas"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw permanent image
        painter.drawImage(0, 0, self.image)
        
        # Draw active rings (not yet permanent)
        for ring in self.ink_rings:
            color = QColor(ring.color)
            
            if ring.ring_type == 'surfactant':
                opacity = int(255 * ring.strength * ring.opacity * 0.3)
                color = QColor(255, 255, 255, opacity)
            else:
                opacity = int(255 * ring.strength * ring.opacity)
                color.setAlpha(opacity)
            
            pen = QPen(color)
            pen.setWidthF(self.ring_thickness)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            
            # Check if ring is significantly deformed
            max_offset = max(abs(p['offset']) for p in ring.distortion_points)
            
            if max_offset > 1.0:
                # Draw as deformed polygon
                from PyQt5.QtGui import QPainterPath
                path = QPainterPath()
                
                # Start at first point
                x0, y0 = ring.get_point_position(0)
                path.moveTo(x0, y0)
                
                # Draw smooth curve through all points
                for i in range(1, ring.num_points + 1):
                    idx = i % ring.num_points
                    x, y = ring.get_point_position(idx)
                    path.lineTo(x, y)
                
                painter.drawPath(path)
            else:
                # Draw as simple circle
                painter.drawEllipse(
                    QPointF(ring.x, ring.y),
                    ring.radius,
                    ring.radius
                )
        
        # Draw turbulence particles
        for particle in self.particles:
            color = QColor(particle.color)
            opacity = int(255 * particle.strength * (1.0 - particle.age / 200.0))
            color.setAlpha(opacity)
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(
                QPointF(particle.x, particle.y),
                particle.radius,
                particle.radius
            )
        
        # Draw brush preview
        if self.mouse_pos and not self.is_touching:
            preview_color = QColor(self.brush_color)
            preview_color.setAlpha(128)
            painter.setPen(QPen(preview_color, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(
                self.mouse_pos,
                self.brush_size,
                self.brush_size
            )
        
        # Draw active touch indicator with color based on button
        if self.is_touching and self.mouse_pos:
            # Show hold duration as expanding circle
            hold_duration = self.elapsed_timer.elapsed()
            duration_factor = min(hold_duration / 500.0, 1.0)
            
            # Different color for ink (red) vs surfactant (blue)
            indicator_color = Qt.red if self.current_button == Qt.LeftButton else Qt.blue
            
            painter.setPen(QPen(indicator_color, 3))
            painter.setBrush(Qt.NoBrush)
            # Outer ring grows with hold time
            extra_radius = 5 + (duration_factor * 15)
            painter.drawEllipse(
                self.mouse_pos,
                self.brush_size + extra_radius,
                self.brush_size + extra_radius
            )
        
        painter.end()
        
    def clear_canvas(self):
        """Clear the canvas"""
        self.image.fill(QColor(240, 240, 245))
        self.ink_rings.clear()
        self.particles.clear()
        self.update()
        
    def save_image(self, filename):
        """Save the current artwork"""
        return self.image.save(filename)


class SuminagashiMainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Suminagashi Marbling Simulator")
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # Create canvas
        self.canvas = SuminagashiCanvas(800, 600)
        main_layout.addWidget(self.canvas, stretch=1)
        
        # Create control panel
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # Set initial values
        self.update_color_preview()
        
    def create_control_panel(self):
        """Create the control panel with all parameters"""
        panel = QWidget()
        panel.setMaximumWidth(350)
        layout = QVBoxLayout(panel)
        
        # Brush Controls
        brush_group = QGroupBox("Brush Settings")
        brush_layout = QGridLayout()
        
        # Color picker
        brush_layout.addWidget(QLabel("Ink Color:"), 0, 0)
        self.color_button = QPushButton()
        self.color_button.setFixedSize(60, 30)
        self.color_button.clicked.connect(self.pick_color)
        brush_layout.addWidget(self.color_button, 0, 1)
        
        # Preset colors
        preset_layout = QHBoxLayout()
        preset_colors = [
            ("Black", QColor(0, 0, 0)),
            ("Red", QColor(180, 0, 0)),
            ("Blue", QColor(0, 0, 180)),
            ("Gold", QColor(180, 140, 0))
        ]
        for name, color in preset_colors:
            btn = QPushButton()
            btn.setFixedSize(30, 30)
            btn.setStyleSheet(f"background-color: {color.name()};")
            btn.clicked.connect(lambda checked, c=color: self.set_preset_color(c))
            preset_layout.addWidget(btn)
        brush_layout.addLayout(preset_layout, 0, 2)
        
        # Brush size
        brush_layout.addWidget(QLabel("Brush Size:"), 1, 0)
        self.brush_size_slider = QSlider(Qt.Horizontal)
        self.brush_size_slider.setRange(5, 100)
        self.brush_size_slider.setValue(30)
        self.brush_size_slider.valueChanged.connect(self.on_brush_size_changed)
        brush_layout.addWidget(self.brush_size_slider, 1, 1, 1, 2)
        self.brush_size_label = QLabel("30")
        brush_layout.addWidget(self.brush_size_label, 1, 3)
        
        # Ink amount
        brush_layout.addWidget(QLabel("Ink Amount:"), 2, 0)
        self.ink_amount_slider = QSlider(Qt.Horizontal)
        self.ink_amount_slider.setRange(10, 100)
        self.ink_amount_slider.setValue(50)
        self.ink_amount_slider.valueChanged.connect(self.on_ink_amount_changed)
        brush_layout.addWidget(self.ink_amount_slider, 2, 1, 1, 2)
        self.ink_amount_label = QLabel("50%")
        brush_layout.addWidget(self.ink_amount_label, 2, 3)
        

        
        brush_group.setLayout(brush_layout)
        layout.addWidget(brush_group)
        
        # Physics Controls
        physics_group = QGroupBox("Water Physics")
        physics_layout = QGridLayout()
        
        # Expansion speed
        physics_layout.addWidget(QLabel("Expansion Speed:"), 0, 0)
        self.expansion_slider = QSlider(Qt.Horizontal)
        self.expansion_slider.setRange(1, 50)
        self.expansion_slider.setValue(15)
        self.expansion_slider.valueChanged.connect(self.on_expansion_changed)
        physics_layout.addWidget(self.expansion_slider, 0, 1)
        self.expansion_label = QLabel("1.5")
        physics_layout.addWidget(self.expansion_label, 0, 2)
        
        # Randomness
        physics_layout.addWidget(QLabel("Randomness:"), 1, 0)
        self.randomness_slider = QSlider(Qt.Horizontal)
        self.randomness_slider.setRange(0, 50)
        self.randomness_slider.setValue(10)
        self.randomness_slider.valueChanged.connect(self.on_randomness_changed)
        physics_layout.addWidget(self.randomness_slider, 1, 1)
        self.randomness_label = QLabel("0.10")
        physics_layout.addWidget(self.randomness_label, 1, 2)
        
        # Surface tension
        physics_layout.addWidget(QLabel("Surface Tension:"), 2, 0)
        self.tension_slider = QSlider(Qt.Horizontal)
        self.tension_slider.setRange(0, 100)
        self.tension_slider.setValue(50)
        self.tension_slider.valueChanged.connect(self.on_tension_changed)
        physics_layout.addWidget(self.tension_slider, 2, 1)
        self.tension_label = QLabel("0.50")
        physics_layout.addWidget(self.tension_label, 2, 2)
        
        # Turbulence
        physics_layout.addWidget(QLabel("Turbulence:"), 3, 0)
        self.turbulence_slider = QSlider(Qt.Horizontal)
        self.turbulence_slider.setRange(0, 100)
        self.turbulence_slider.setValue(20)
        self.turbulence_slider.valueChanged.connect(self.on_turbulence_changed)
        physics_layout.addWidget(self.turbulence_slider, 3, 1)
        self.turbulence_label = QLabel("0.20")
        physics_layout.addWidget(self.turbulence_label, 3, 2)
        
        # Interaction strength
        physics_layout.addWidget(QLabel("Ring Interaction:"), 4, 0)
        self.interaction_slider = QSlider(Qt.Horizontal)
        self.interaction_slider.setRange(0, 200)
        self.interaction_slider.setValue(100)
        self.interaction_slider.valueChanged.connect(self.on_interaction_changed)
        physics_layout.addWidget(self.interaction_slider, 4, 1)
        self.interaction_label = QLabel("1.00")
        physics_layout.addWidget(self.interaction_label, 4, 2)
        
        physics_group.setLayout(physics_layout)
        layout.addWidget(physics_group)
        
        # Visual Controls
        visual_group = QGroupBox("Visual Settings")
        visual_layout = QGridLayout()
        
        # Ring thickness
        visual_layout.addWidget(QLabel("Ring Thickness:"), 0, 0)
        self.thickness_slider = QSlider(Qt.Horizontal)
        self.thickness_slider.setRange(1, 20)
        self.thickness_slider.setValue(3)
        self.thickness_slider.valueChanged.connect(self.on_thickness_changed)
        visual_layout.addWidget(self.thickness_slider, 0, 1)
        self.thickness_label = QLabel("3.0")
        visual_layout.addWidget(self.thickness_label, 0, 2)
        
        visual_group.setLayout(visual_layout)
        layout.addWidget(visual_group)
        
        # Action buttons
        button_layout = QVBoxLayout()
        
        clear_button = QPushButton("Clear Canvas")
        clear_button.clicked.connect(self.canvas.clear_canvas)
        button_layout.addWidget(clear_button)
        
        save_button = QPushButton("Save Artwork")
        save_button.clicked.connect(self.save_artwork)
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)
        
        # Instructions
        instructions = QLabel(
            "Instructions:\n"
            "• LEFT CLICK = Ink\n"
            "• RIGHT CLICK = Surfactant\n"
            "• Hold longer = more dipping time\n"
            "• Watch the expanding ring!\n"
            "• Experiment with settings!"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("QLabel { padding: 10px; background-color: #f0f0f0; }")
        layout.addWidget(instructions)
        
        layout.addStretch()
        
        return panel
        
    def pick_color(self):
        """Open color picker dialog"""
        color = QColorDialog.getColor(self.canvas.brush_color, self)
        if color.isValid():
            self.canvas.set_brush_color(color)
            self.update_color_preview()
            
    def set_preset_color(self, color):
        """Set a preset color"""
        self.canvas.set_brush_color(color)
        self.update_color_preview()
        
    def update_color_preview(self):
        """Update the color button preview"""
        color = self.canvas.brush_color
        self.color_button.setStyleSheet(
            f"background-color: {color.name()}; border: 2px solid #333;"
        )
        
    def on_brush_size_changed(self, value):
        """Handle brush size slider change"""
        self.canvas.set_brush_size(value)
        self.brush_size_label.setText(str(value))
        
    def on_ink_amount_changed(self, value):
        """Handle ink amount slider change"""
        self.canvas.set_ink_amount(value)
        self.ink_amount_label.setText(f"{value}%")
        

    def on_expansion_changed(self, value):
        """Handle expansion speed slider change"""
        speed = value / 10.0
        self.canvas.set_expansion_speed(speed)
        self.expansion_label.setText(f"{speed:.1f}")
        
    def on_randomness_changed(self, value):
        """Handle randomness slider change"""
        randomness = value / 100.0
        self.canvas.set_randomness(randomness)
        self.randomness_label.setText(f"{randomness:.2f}")
        
    def on_tension_changed(self, value):
        """Handle surface tension slider change"""
        tension = value / 100.0
        self.canvas.set_surface_tension(tension)
        self.tension_label.setText(f"{tension:.2f}")
        
    def on_turbulence_changed(self, value):
        """Handle turbulence slider change"""
        turbulence = value / 100.0
        self.canvas.set_turbulence(turbulence)
        self.turbulence_label.setText(f"{turbulence:.2f}")
        
    def on_interaction_changed(self, value):
        """Handle ring interaction slider change"""
        interaction = value / 100.0
        self.canvas.set_interaction_strength(interaction)
        self.interaction_label.setText(f"{interaction:.2f}")
        
    def on_thickness_changed(self, value):
        """Handle ring thickness slider change"""
        thickness = value / 1.0
        self.canvas.set_ring_thickness(thickness)
        self.thickness_label.setText(f"{thickness:.1f}")
        
    def save_artwork(self):
        """Save the current artwork to file"""
        from PyQt5.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Artwork",
            "suminagashi.png",
            "PNG Images (*.png);;All Files (*)"
        )
        if filename:
            if self.canvas.save_image(filename):
                print(f"Artwork saved to {filename}")
            else:
                print("Failed to save artwork")


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = SuminagashiMainWindow()
    window.resize(1200, 700)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
