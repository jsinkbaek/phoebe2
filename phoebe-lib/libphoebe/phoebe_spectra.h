#ifndef PHOEBE_SPECTRA_H
	#define PHOEBE_SPECTRA_H 1

#include "phoebe_types.h"

typedef struct PHOEBE_specrep_tag {
	int resolution;
	int lambda_min;
	int lambda_max;
	int temperature;
	int metallicity;
	int gravity;
} PHOEBE_specrep_tag;

typedef struct PHOEBE_specrep {
	int                  no;
	PHOEBE_specrep_tag *prop;
} PHOEBE_specrep;

int              query_spectra_repository                    (char *rep_name, PHOEBE_specrep *spec);

PHOEBE_spectrum *phoebe_spectrum_new                         ();
PHOEBE_spectrum *phoebe_spectrum_new_from_file               (char *filename);
PHOEBE_spectrum *phoebe_spectrum_create                      (double ll, double ul, double R, PHOEBE_spectrum_dispersion disp);
PHOEBE_spectrum *phoebe_spectrum_duplicate                   (PHOEBE_spectrum *spectrum);
PHOEBE_vector   *phoebe_spectrum_get_column                  (PHOEBE_spectrum *spectrum, int col);
int              phoebe_spectrum_new_from_repository         (PHOEBE_spectrum **spectrum, double R, int T, int g, int M, double ll, double ul);
int              phoebe_spectrum_alloc                       (PHOEBE_spectrum *spectrum, int dim);
int              phoebe_spectrum_realloc                     (PHOEBE_spectrum *spectrum, int dim);
int              phoebe_spectrum_free                        (PHOEBE_spectrum *spectrum);
int              phoebe_spectrum_rebin                       (PHOEBE_spectrum **src, PHOEBE_spectrum_dispersion disp, double ll, double ul, double R);
int              phoebe_spectrum_integrate                   (PHOEBE_spectrum *spectrum, double ll, double ul, double *result);
int              phoebe_spectrum_broaden                     (PHOEBE_spectrum **dest, PHOEBE_spectrum *src, double R);
int              phoebe_spectrum_crop                        (PHOEBE_spectrum *spectrum, double ll, double ul);
int              phoebe_spectrum_apply_doppler_shift         (PHOEBE_spectrum **dest, PHOEBE_spectrum *src, double velocity);
int              phoebe_spectrum_apply_rotational_broadening (PHOEBE_spectrum **dest, PHOEBE_spectrum *src, double vsini, double ldx);
int              phoebe_spectrum_set_sampling                (PHOEBE_spectrum *spectrum, double Rs);
int              phoebe_spectrum_set_resolution              (PHOEBE_spectrum *spectrum, double R);
int              phoebe_spectrum_multiply_by                 (PHOEBE_spectrum **dest, PHOEBE_spectrum *src, double factor);
int              phoebe_spectrum_dispersion_guess            (PHOEBE_spectrum_dispersion *disp, PHOEBE_spectrum *spectrum);
char            *phoebe_spectrum_dispersion_type_get_name    (PHOEBE_spectrum_dispersion disp);

int              phoebe_spectra_add                          (PHOEBE_spectrum **dest, PHOEBE_spectrum *src1, PHOEBE_spectrum *src2);
int              phoebe_spectra_subtract                     (PHOEBE_spectrum **dest, PHOEBE_spectrum *src1, PHOEBE_spectrum *src2);
int              phoebe_spectra_merge                        (PHOEBE_spectrum **dest, PHOEBE_spectrum *src1, PHOEBE_spectrum *src2, double w1, double w2, double ll, double ul, double Rs);
int              phoebe_spectra_multiply                     (PHOEBE_spectrum **dest, PHOEBE_spectrum *src1, PHOEBE_spectrum *src2, double ll, double ul, double R);

#endif
