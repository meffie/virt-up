{% raw -%}
#!/bin/sh
old_iface=`awk '$1=="iface" && $2!="lo" && $3=="inet" {print $2}' /etc/network/interfaces | tail -1`
new_iface=`ip -o -a link | awk '$2!="lo:" {print $2}' | tr -d : | tail -1`

echo "* Old interface is '$old_iface'."
echo "* New interface is '$new_iface'."

if test "x$new_iface" = "x"; then
    echo "* Enable to detect primary interface." >&2
elif test "x$old_iface" != "x$new_iface"; then
    echo "* Changing '$old_iface' to '$new_iface' in '/etc/network/interfaces'."
    sed -i -e "s/$old_iface/$new_iface/" /etc/network/interfaces
    echo "* Bringing up interface '$new_iface'."
    ifup "$new_iface"
fi
{%- endraw %}
