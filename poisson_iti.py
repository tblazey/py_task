#!/usr/bin/python

# Load libraries
import argparse
import numpy as np
import scipy.optimize as opt


def get_args():
    """
    Function to parse input arguments
    """
    
    # Create parser
    parser = argparse.ArgumentParser(
        description="Generate trial intervals/timings according to an approximate poisson process"
    )
    parser.add_argument("n", type=int, help="Number of trials")
    parser.add_argument("min", type=float, help="Minimum iti (s)")
    parser.add_argument("mean", type=float, help="Mean iti (s)")
    parser.add_argument("max", type=float, help="Maximum iti (s)")
    parser.add_argument("out", type=str, help="Name of output file")
    parser.add_argument(
        "-bins",
        type=float,
        help="Number of bins for histogram fitting. Default is 12.",
        default=12,
    )
    parser.add_argument(
        "-delay",
        type=float,
        help="Time to wait before trials. Default is 0.",
        default=0,
    )
    parser.add_argument(
        "-plot",
        help="Save histogram of trial intervals",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-tr",
        help="Frame duration (s). If specified output will include rounded frame indicators",
    )
    parser.add_argument(
        "-tol",
        default=0.01,
        type=float,
        help="Acceptable difference between requested iti limits and optimized ones"
             "Default is 0.01"
    )
    return parser.parse_args()


# Function to generate sse between current histogram and exponential process
def cost(x, y, bins, pdf):
    hat = x + y
    dens, _ = np.histogram(hat, bins=bins, density=True)
    return np.nansum(np.power(pdf - dens, 2))


# Function defining nonlinear constraints
def nlc_wrap(y):
    def nl_func(x):
        hat = x + y
        return np.array([np.min(hat), np.max(hat)])

    return nl_func


def poisson_iti(
    n_trial, min_iti, mean_iti, max_iti, n_bin=12, delay=0, tr=None, tol=0.01
):
    """
    Generates inter-trial intervals and timings according to an approximate poisson
    process

    Parameters
    ----------
    n_trial : int
       Number of trials
    min_iti : float
       Minimum inter-trial interval (s)
    mean_iti : float
       Mean inter-trial interval (s)
    max_iti : float
       Maximum inter-trial interval (s)
    n_bin : int
       Number of bins for histogram/PDF fitting
    delay : float
       Delay before starting trials (s)
    tr : float
       Time between frames (s)
    tol : float
        Acceptable difference between optimized time intervals and requested constraints

    Returns
    -------
    iti : array
       Array of shape n_trial with inter-trial intervals that approximate a
       poisson process. Values have a minimum of min_iti, a maximum of max_iti, and a
       mean of mean_iti.
    t : array
       Array of trial start times
    ifi : array
       If tr specified, converts iti to zero-based frame indices.
    tf : array
       If tr specified, converts t to zero-based frame indices.
    """

    # Define params of desired exponential distribution
    exp_min = 0
    exp_max = max_iti - min_iti
    exp_lmbda = mean_iti - min_iti
    exp_sum = n_trial * exp_lmbda
    exp_mean = 1 / exp_lmbda
    
    while True:

        # Generate initial itis
        iti = np.random.exponential(exp_lmbda, n_trial)
        iti[iti > exp_max] = exp_max

        # Compute simulated and expected pdf given input parameters
        dens, bins = np.histogram(iti, bins=n_bin, density=True)
        delta_bin = bins[1] - bins[0]
        pdf = (
            np.exp(-exp_mean * bins) - np.exp(-exp_mean * (bins + delta_bin))
        ) / delta_bin

        # Define constraints (linear is trial duration, nonlinear is minimum  and maximum iti)
        exp_diff = exp_sum - np.sum(iti)
        sum_con = opt.LinearConstraint(np.ones((1, n_trial)), lb=exp_diff, ub=exp_diff)
        range_con = opt.NonlinearConstraint(
            nlc_wrap(iti), lb=[exp_min, exp_max], ub=[exp_min, exp_max]
        )

        # Adjust init to fit average constraint
        init = np.ones(n_trial) * exp_diff / n_trial
        fit = opt.minimize(
            cost, init, args=(iti, bins, pdf[0:-1]), constraints=[sum_con, range_con]
        )
        
        # Generate timings for output
        iti_hat = iti + fit.x + min_iti
        dur_hat = np.cumsum(iti_hat) + delay
        
        """
        Make sure optimization succeeded. If not, rerun.
        This is a horrible hack, but is necessary until I can figure out
        why the constraints are violated. My current guess is that is due to the fact
        that the initial guess does not meet the min/max constraints.
        """
        fit_cons = [np.min(iti_hat), np.mean(iti_hat), np.max(iti_hat)]
        cons = [min_iti, mean_iti, max_iti]
        if np.allclose(fit_cons, cons, atol=tol):
            break

    if tr is None:
        return iti_hat, dur_hat
    return iti_hat, dur_hat, np.round(iti_hat / tr), np.round(dur_hat / tr)


def main():
    # Run parser
    args = get_args()

    # Get trial timings
    p_times = poisson_iti(
        args.n,
        args.min,
        args.mean,
        args.max,
        n_bin=args.bins,
        delay=args.delay,
        tr=args.tr,
        tol=args.tol
    )

    # Write output
    header = "iti,time"
    fmt = ["%.5f", "%.5f"]
    if args.tr is not None:
        header += "frame.iti,frame.idx"
        fmt += ["%i", "%i"]
    np.savetxt(args.out + ".csv", np.array(p_times).T, delimiter=",", fmt=fmt)


if __name__ == "__main__":
    main()
