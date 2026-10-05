#ifndef __ETA_SCHEDULE_H__
#define __ETA_SCHEDULE_H__

// The adaptive learning rate of class 12.1: a single eta for the whole network, moved by how the error goes
// from one epoch to the next. It only sees the error values, nothing about the network or the data.

typedef struct {
  double increase;       // a: added to eta after patience_up epochs in a row with the error going down
  double decrease;       // b: eta becomes eta * (1 - b) after patience_down epochs in a row with it going up
  int patience_up;       // k
  int patience_down;     // k'
  int falling;           // current streaks
  int rising;
  int has_previous;
  double previous_error;
} EtaSchedule;

EtaSchedule eta_schedule_new(double increase, double decrease, int patience_up, int patience_down);

// Takes the error of one more epoch and returns the eta to go on with. Eta grows by adding and shrinks by
// multiplying: slowly up, quickly down, since too large an eta can diverge and too small one is only slow.
// An error equal to the previous one breaks both streaks: on a plateau the error repeats exactly, and
// counting that as going up would shrink eta towards 0 right where it needs to move.
double eta_schedule_update(EtaSchedule * schedule, double eta, double error);

#endif //__ETA_SCHEDULE_H__
