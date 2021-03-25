{% raw -%}
#!/bin/sh
new_iface=`ip -o -a link | awk '$2!="lo:" {print $2}' | tr -d : | tail -1`
echo "* New interface is '$new_iface'."
if test "x$new_iface" = "x"; then
    echo "* Unable to detect primary interface." >&2
    exit 1
fi
echo "* Setting interface name to '$new_iface' in '/etc/netplan/01-netcfg.yaml'."
sed -i -e "s/^    en.*:/    $new_iface:/" /etc/netplan/01-netcfg.yaml
echo "* Bringing up interface '$new_iface'."
netplan apply
{%- endraw %}
