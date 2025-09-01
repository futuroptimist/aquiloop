// Duckweed scooper - parametric design
// TODO: explore mechanical variant in future

handle_length = 220; // mm
handle_diameter = 10; // mm
scooper_width = 45; // mm
scooper_depth = 15; // mm
wall_thickness = 2.5; // mm

module handle() {
    cylinder(h = handle_length, r = handle_diameter / 2, $fn = 64);
}

module scooper_head() {
    difference() {
        cube([scooper_width, scooper_depth, wall_thickness]);
        translate([wall_thickness, wall_thickness, 0])
            cube([scooper_width - 2 * wall_thickness,
                  scooper_depth - 2 * wall_thickness,
                  wall_thickness]);
    }
}

module duckweed_scooper() {
    translate([0, 0, wall_thickness]) rotate([90, 0, 0]) handle();
    translate([-scooper_width / 2, -scooper_depth, 0]) scooper_head();
}

duckweed_scooper();
