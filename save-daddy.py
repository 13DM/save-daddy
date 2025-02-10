bl_info = {
    "name": "Save Daddy Autosaving",
    "author": "Dad (13DM)",
    "version": (1, 0, 3),
    "blender": (3, 6, 5),
    "location": "Preferences > Add-ons",
    "description": ("Automatically autosaves your blend file every 5 minutes (default) "
                    "with a timestamp appended to the filename and manages backups."),
    "warning": "",
    "wiki_url": "https://github.com/13DM/save-daddy",
    "category": "System",
}

import bpy
import os
from datetime import datetime
from bpy.app.handlers import persistent

# Global flag used to cancel the autosave timer when the add-on is disabled.
autosave_running = True

# Global flag to ensure we only prompt for a save once per session.
has_prompted_save = False


# ---------------------------------------------------------------
# Helper: Build an override context for operator calls
# We need to do this as file operations need context where we may not have it
# ---------------------------------------------------------------
def get_override_context():
    """Return an override context dictionary for calling operators from a timer."""
    ctx = bpy.context.copy()
    wm = bpy.context.window_manager
    if wm.windows:
        window = wm.windows[0]
        ctx['window'] = window
        ctx['screen'] = window.screen
        # Look for an area that is likely to be valid for file operations.
        for area in window.screen.areas:
            if area.type in {'VIEW_3D', 'INFO', 'TEXT_EDITOR'}:
                ctx['area'] = area
                # Find a region of type 'WINDOW'
                for region in area.regions:
                    if region.type == 'WINDOW':
                        ctx['region'] = region
                        return ctx
    return ctx


# ---------------------------------------------------------------
# Add-on Preferences (The settings to control the autosave values)
# ---------------------------------------------------------------
class AutosavePreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    autosave_interval: bpy.props.FloatProperty(
        name="Autosave Interval (seconds)",
        default=300.0,
        min=30.0,
        description="Time interval between autosaves (in seconds). Setting this too low can cause the UI to lock up"
    )

    max_backup_files: bpy.props.IntProperty(
        name="Maximum Backup Files",
        default=1,
        min=1,
        description="Number of backup files to keep (older files will be removed)"
    )

    default_save_path: bpy.props.StringProperty(
        name="Default Save Path",
        default="",
        subtype='DIR_PATH',
        description=(
            "If the current file is unsaved or in a forbidden location, autosaves will be saved here. \n"
            "Leave empty to prompt for saving."
        )
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "autosave_interval")
        layout.prop(self, "max_backup_files")
        layout.prop(self, "default_save_path")


# ---------------------------------------------------------------
# Operator to Prompt the User to Save (only once per session)
# We do this if the default path isn't provided. Otherwise user will not be prompted.
# ---------------------------------------------------------------
class AUTOSAVE_OT_PromptSave(bpy.types.Operator):
    """Prompt to Save Your Blend File"""
    bl_idname = "wm.autosave_prompt_save"
    bl_label = "Please Save Your File"

    def execute(self, context):
        bpy.ops.wm.save_as_mainfile('INVOKE_DEFAULT')
        return {'FINISHED'}


# ---------------------------------------------------------------
# The Timer Function (called every autosave_interval seconds)
# ---------------------------------------------------------------
def autosave_timer():
    global autosave_running, has_prompted_save

    # Debug print to verify the timer is running.
    print("[Timed Autosave] Timer triggered")

    if not autosave_running:
        return None  # Returning None stops the timer.

    # Get add-on preferences.
    try:
        prefs = bpy.context.preferences.addons[__name__].preferences
    except Exception as e:
        print("[Timed Autosave] Could not get preferences:", e)
        return 300.0  # Retry in 300 seconds if preferences aren’t available.
    interval = prefs.autosave_interval

    current_filepath = bpy.data.filepath

    # Determine system temporary directories.
    temp_dirs = []
    if os.name == 'nt':
        temp_dirs = [os.getenv('TEMP'), os.getenv('TMP')]
    else:
        temp_dirs = ['/tmp']
    temp_dirs = [os.path.realpath(d) for d in temp_dirs if d]

    # Blender installation folder.
    install_dir = os.path.dirname(bpy.app.binary_path)
    install_dir = os.path.realpath(install_dir)

    # Check if the path is in temp or the install directory.
    def in_forbidden_path(path):
        if not path:
            return False
        path = os.path.realpath(path)
        for t in temp_dirs:
            if path.startswith(t):
                return True
        if path.startswith(install_dir):
            return True
        return False

    # Determine where to save the autosave file.
    if current_filepath and not in_forbidden_path(current_filepath):
        # Use the directory of the current file.
        base_dir = os.path.dirname(current_filepath)
        base_name = os.path.splitext(os.path.basename(current_filepath))[0]
    else:
        # Either unsaved or in a forbidden location.
        if prefs.default_save_path and os.path.isdir(bpy.path.abspath(prefs.default_save_path)):
            base_dir = bpy.path.abspath(prefs.default_save_path)
            base_name = (os.path.splitext(os.path.basename(current_filepath))[0]
                         if current_filepath else "untitled")
        else:
            # No valid path available: prompt the user once.
            if not current_filepath and not has_prompted_save:
                has_prompted_save = True
                bpy.ops.wm.autosave_prompt_save('INVOKE_DEFAULT')
            return interval  # Skip this autosave cycle.

    # Build the new filename with a 24-hour timestamp.
    timestamp = datetime.now().strftime("%d_%m_%Y_%H-%M")
    new_filename = f"{base_name}_{timestamp}.blend"
    new_filepath = os.path.join(base_dir, new_filename)

    # Get a proper override context.
    override = get_override_context()
    try:
        bpy.ops.wm.save_as_mainfile(override, filepath=new_filepath, copy=True)
        print(f"[Timed Autosave] Autosaved to: {new_filepath}")
    except Exception as e:
        print("[Timed Autosave] Autosave failed:", e)

    # ---------------------------------------------------------------
    # Backup Management: Remove older autosave files if necessary.
    # ---------------------------------------------------------------
    try:
        backup_files = []
        for f in os.listdir(base_dir):
            if f.startswith(base_name + "_") and f.endswith(".blend"):
                full_path = os.path.join(base_dir, f)
                backup_files.append(full_path)
        backup_files.sort(key=lambda f: os.path.getmtime(f))
        while len(backup_files) > prefs.max_backup_files:
            file_to_remove = backup_files.pop(0)
            try:
                os.remove(file_to_remove)
                print(f"[Timed Autosave] Removed old autosave: {file_to_remove}")
            except Exception as e:
                print("[Timed Autosave] Failed to remove old autosave:", e)
    except Exception as e:
        print("[Timed Autosave] Backup management error:", e)

    return interval  # Reschedule this timer callback after the interval.


# ---------------------------------------------------------------
# Function to Start the Timer (called on file load and add-on registration)
# ---------------------------------------------------------------
def start_autosave_timer():
    # (Re)start the timer. The timer function returns the interval, so it repeats.
    bpy.app.timers.register(autosave_timer, first_interval=1.0)


# ---------------------------------------------------------------
# Handler to Start Autosave When a File is Loaded
# ---------------------------------------------------------------
@persistent
def load_post_handler(dummy):
    start_autosave_timer()


# ---------------------------------------------------------------
# Registration
# ---------------------------------------------------------------
classes = (
    AutosavePreferences,
    AUTOSAVE_OT_PromptSave,
)

def register():
    global autosave_running, has_prompted_save
    autosave_running = True
    has_prompted_save = False
    for cls in classes:
        bpy.utils.register_class(cls)
    if load_post_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_post_handler)
    # Start the timer immediately.
    start_autosave_timer()
    print("[Timed Autosave] Add-on enabled and timer started.")

def unregister():
    global autosave_running
    autosave_running = False  # This causes the timer to stop.
    if load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_handler)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("[Timed Autosave] Add-on disabled.")

if __name__ == "__main__":
    register()
