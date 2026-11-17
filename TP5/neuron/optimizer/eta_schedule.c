#include "eta_schedule.h"


EtaSchedule eta_schedule_new(double increase, double decrease, int patience_up, int patience_down) {
  return (EtaSchedule) {
    .increase = increase,
    .decrease = decrease,
    .patience_up = patience_up,
    .patience_down = patience_down,
  };
}


double eta_schedule_update(EtaSchedule * schedule, double eta, double error) {

  int had_previous = schedule->has_previous;
  double previous = schedule->previous_error;
  schedule->has_previous = 1;
  schedule->previous_error = error;
  if (!had_previous) return eta;

  if (error < previous) {
    schedule->falling++;
    schedule->rising = 0;
  } else if (error > previous) {
    schedule->rising++;
    schedule->falling = 0;
  } else {
    schedule->falling = 0;
    schedule->rising = 0;
  }

  if (schedule->falling >= schedule->patience_up) {
    schedule->falling = 0;
    return eta + schedule->increase;
  }
  if (schedule->rising >= schedule->patience_down) {
    schedule->rising = 0;
    return eta * (1.0 - schedule->decrease);
  }
  return eta;

}
