#!/bin/sh
set -eu

source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
install_dir="${HOME}/.local/share/calc-es"
applications_dir="${HOME}/.local/share/applications"

if ! /usr/bin/python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' >/dev/null 2>&1; then
  printf 'Calc ES needs GTK 3 for its native desktop interface.\n' >&2
  printf 'Install it with: sudo apt install python3-gi gir1.2-gtk-3.0\n' >&2
  exit 1
fi

mkdir -p "$install_dir" "$applications_dir"
cp "$source_dir/toto.py" "$install_dir/toto_app.py"
cp "$source_dir/logo.svg" "$install_dir/"
chmod 755 "$install_dir/toto_app.py"

cat > "$install_dir/launch.sh" <<'LAUNCHER'
#!/bin/sh
exec /usr/bin/python3 "$HOME/.local/share/calc-es/toto_app.py"
LAUNCHER
chmod 755 "$install_dir/launch.sh"

desktop_exec=$(printf '%s' "$install_dir/launch.sh" | sed 's/\\/\\\\/g; s/ /\\ /g')
cat > "$applications_dir/calc-es.desktop" <<DESKTOP_ENTRY
[Desktop Entry]
Version=1.0
Type=Application
Name=Calc ES
Comment=Native scientific calculator and mathematics workbench
Exec=$desktop_exec
Icon=$install_dir/logo.svg
Terminal=false
Categories=Education;Utility;
DESKTOP_ENTRY
chmod 644 "$applications_dir/calc-es.desktop"

printf 'Calc ES is installed. Find it in the Linux Mint application menu under Education or Utility.\n'
