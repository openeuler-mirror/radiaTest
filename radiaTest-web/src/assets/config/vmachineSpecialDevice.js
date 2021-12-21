const specialDevice = [
  {
    service: 'spice-webdavd.service',
    device: `<channel type='spiceport'>
  <source channel='org.spice-space.webdav.0' />
  <target type='virtio' name='org.spice-space.webdav.0' />
</channel>
    `
  },
  {
    service: 'qemu-guest-agent.service',
    device: `<channel type='unix'>
  <source mode='bind' path='/var/lib/libvirt/qemu/org.qemu.guest_agent.0' />
  <target type='virtio' name='org.qemu.guest_agent.0' />
  <address type='virtio-serial' controller='0' bus='0' port='2' />
</channel>
    `
  },
];

export {
  specialDevice,
};
