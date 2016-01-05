drop table if exists devices;

create table devices (
  id integer primary key autoincrement,
  name text not null,         --pref. name of device
  description text,           --device description, otpional
  type text not null,         --device type: input or output
  pin int,                    --pin the device uses
  state int,                  --only for output devices 0 = false, 1 = true, null for other devices
  module text                 --path to module of this device
);

insert into devices values (1, "Temp Sensor 3000", "best sensor in the universe", "input", 18, null, "modules/gpio_input.py");
insert into devices values (2, "motor", "best actor in the universe", "input", 16, null, "modules/gpio_input.py");
