"""
Simple dialog for editing display metadata (clean names for UI).
Original search metadata remains immutable.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFrame
)
from PySide6.QtCore import Signal, Qt
from ui.style_manager import StyleManager


class MultiMetadataEditorDialog(QDialog):
    """Dialog for editing clean display metadata
    
    Shows original metadata (read-only) and allows editing display fields only.
    Original track_name and artist_name are preserved for lyrics search accuracy.
    """
    
    metadata_saved = Signal(dict)  # Emits {track_name_display, artist_name_display}
    
    def __init__(self, metadata: dict, parent=None):
        super().__init__(parent)
        self.metadata = metadata
        
        self.setWindowTitle("Edit Display Metadata")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        self._setup_ui()
        self._apply_styles()
        self._populate_fields()
    
    def _setup_ui(self):
        """Create the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Title
        title_label = QLabel("Edit Display Names")
        title_label.setObjectName("title_label")
        layout.addWidget(title_label)
        
        # Info text
        info_label = QLabel(
            "Edit the display names shown in the UI. "
            "Original metadata is preserved for lyrics search."
        )
        info_label.setObjectName("info_label")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setObjectName("separator")
        layout.addWidget(separator1)
        
        # Original metadata (read-only reference)
        original_group = QVBoxLayout()
        original_group.setSpacing(10)
        
        original_header = QLabel("Original Metadata (for lyrics search):")
        original_header.setObjectName("section_header")
        original_group.addWidget(original_header)
        
        # Original track name
        self.original_track_label = QLabel()
        self.original_track_label.setObjectName("readonly_field")
        original_group.addWidget(self.original_track_label)
        
        # Original artist name
        self.original_artist_label = QLabel()
        self.original_artist_label.setObjectName("readonly_field")
        original_group.addWidget(self.original_artist_label)
        
        layout.addLayout(original_group)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setObjectName("separator")
        layout.addWidget(separator2)
        
        # Editable display metadata
        display_group = QVBoxLayout()
        display_group.setSpacing(15)
        
        display_header = QLabel("Display Names (shown in UI):")
        display_header.setObjectName("section_header")
        display_group.addWidget(display_header)
        
        # Display track name
        track_display_layout = QVBoxLayout()
        track_display_layout.setSpacing(5)
        track_display_label = QLabel("Track Name:")
        track_display_label.setObjectName("field_label")
        self.track_display_input = QLineEdit()
        self.track_display_input.setPlaceholderText("Enter clean track name...")
        track_display_layout.addWidget(track_display_label)
        track_display_layout.addWidget(self.track_display_input)
        display_group.addLayout(track_display_layout)
        
        # Display artist name
        artist_display_layout = QVBoxLayout()
        artist_display_layout.setSpacing(5)
        artist_display_label = QLabel("Artist Name:")
        artist_display_label.setObjectName("field_label")
        self.artist_display_input = QLineEdit()
        self.artist_display_input.setPlaceholderText("Enter clean artist name...")
        artist_display_layout.addWidget(artist_display_label)
        artist_display_layout.addWidget(self.artist_display_input)
        display_group.addLayout(artist_display_layout)
        
        layout.addLayout(display_group)
        
        # Spacer
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.cancel_btn = QPushButton("Cancel")
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("primary_button")
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        
        # Connect signals
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self._on_save_clicked)
    
    def _apply_styles(self):
        """Apply StyleManager colors"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {StyleManager.get_color('background')};
            }}
            
            #title_label {{
                font-size: 18px;
                font-weight: bold;
                color: {StyleManager.get_color('accent')};
                margin-bottom: 5px;
            }}
            
            #info_label {{
                color: {StyleManager.get_color('text_dim')};
                font-size: 12px;
                margin-bottom: 10px;
            }}
            
            #section_header {{
                font-size: 13px;
                font-weight: bold;
                color: {StyleManager.get_color('text')};
                margin-top: 5px;
                margin-bottom: 5px;
            }}
            
            #readonly_field {{
                color: {StyleManager.get_color('text_dim')};
                font-size: 12px;
                padding: 5px 10px;
                background-color: {StyleManager.get_color('surface')};
                border-radius: 4px;
                margin-bottom: 3px;
            }}
            
            #field_label {{
                color: {StyleManager.get_color('text')};
                font-size: 12px;
                font-weight: bold;
            }}
            
            QLineEdit {{
                background-color: {StyleManager.get_color('surface')};
                border: 1px solid {StyleManager.get_color('border')};
                border-radius: 4px;
                padding: 8px 12px;
                color: {StyleManager.get_color('text')};
                font-size: 13px;
            }}
            
            QLineEdit:focus {{
                border: 1px solid {StyleManager.get_color('accent')};
            }}
            
            QPushButton {{
                background-color: {StyleManager.get_color('surface')};
                border: 1px solid {StyleManager.get_color('border')};
                border-radius: 4px;
                padding: 8px 20px;
                color: {StyleManager.get_color('text')};
                font-size: 13px;
                min-width: 80px;
            }}
            
            QPushButton:hover {{
                background-color: {StyleManager.get_color('surface_hover')};
                border-color: {StyleManager.get_color('accent')};
            }}
            
            QPushButton#primary_button {{
                background-color: {StyleManager.get_color('accent')};
                border-color: {StyleManager.get_color('accent')};
                color: {StyleManager.get_color('background')};
                font-weight: bold;
            }}
            
            QPushButton#primary_button:hover {{
                background-color: {StyleManager.get_color('accent_hover')};
            }}
            
            #separator {{
                color: {StyleManager.get_color('border')};
                background-color: {StyleManager.get_color('border')};
            }}
        """)
    
    def _populate_fields(self):
        """Populate fields with current metadata"""
        # Original metadata (read-only display)
        track_name = self.metadata.get('track_name', self.metadata.get('title', 'Unknown'))
        artist_name = self.metadata.get('artist_name', self.metadata.get('artist', 'Unknown'))
        
        self.original_track_label.setText(f"🎵 Track: {track_name}")
        self.original_artist_label.setText(f"👤 Artist: {artist_name}")
        
        # Display metadata (editable fields)
        # Use display fields if they exist, otherwise fall back to original
        track_display = self.metadata.get('track_name_display', track_name)
        artist_display = self.metadata.get('artist_name_display', artist_name)
        
        self.track_display_input.setText(track_display)
        self.artist_display_input.setText(artist_display)
    
    def _on_save_clicked(self):
        """Save button clicked - validate and emit signal"""
        track_display = self.track_display_input.text().strip()
        artist_display = self.artist_display_input.text().strip()
        
        if not track_display or not artist_display:
            # Show validation error
            self.track_display_input.setStyleSheet(
                f"border: 2px solid {StyleManager.get_color('error')};"
                if not track_display else ""
            )
            self.artist_display_input.setStyleSheet(
                f"border: 2px solid {StyleManager.get_color('error')};"
                if not artist_display else ""
            )
            return
        
        # Emit saved data (only display fields)
        self.metadata_saved.emit({
            'track_name_display': track_display,
            'artist_name_display': artist_display
        })
        
        self.accept()
