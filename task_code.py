#!/usr/bin/env python

# Import necessary libs and change preferences
import json
import os
import random
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from poisson_iti import poisson_iti
import psychopy

psychopy.prefs.hardware["audioLib"] = ["ptb", "pyo", "pygame", "sounddevice"]
from psychopy import visual, event, core, gui, data, monitors
from psychopy.sound import Microphone
import pyglet

# Function to display stimulus text
def show_stim(stims, time, text=None, show_count=False, show_2=False):
    # Update text if necessary
    if text is not None:
        for stim in stims:
            stim.setText(text)

    # Show debugging count
    if show_count is True:
        count_text.setText(f"{trial_idx:03} / {n_trial:03}")

    # Update window and time
    for stim in stims:
        stim.autoDraw = True
    win_1.flip()
    timer.addTime(time)


# Function to display instructions
def show_instruct(text, screen_2=False, extra=None, wait_key="space"):
    # Show text on screen 1
    inst_text.setText(text)
    inst_text.draw()
    if extra is not None:
        for stim in extra:
            stim.draw()
    win_1.flip()

    # Show text on screen 2 if needed
    if screen_2 is True:
        inst_2_text.setText(text)
        inst_2_text.draw()
        cont_text.setText(f"Press {wait_key} to continue")
        cont_text.draw()
        win_2.flip()

    # Wait for key press to continue
    while True:
        all_keys = event.getKeys()
        if params["keys"]["exit"] in all_keys:
            core.quit()
        elif wait_key in all_keys:
            break


# Function to update progress text
def update_prog(trial):
    update_str = f"Current Scan Block: {scan + 1} / {n_scan}\n\n"
    update_str += f"Current Trial: {trial_idx + 1} / {n_trial}\n\n"
    update_str += f"Total Responses: {n_resp_total} / {trial_idx}\n\n"
    update_str += f"Trial within Block: {trial + 1} / {n_trial_scan[scan]}\n\n"
    update_str += f"Responses within Block: {n_resp_scan} / {trial}"
    update_text.setText(update_str)
    update_text.draw()
    win_2.flip()


# Function for waiting until trigger has occured n times
def wait_trig(n_trig, trig_key, exit_key):
    trig_cnt = 0
    while trig_cnt < n_trig:
        all_keys = event.getKeys()
        if trig_key in all_keys:
            trig_cnt += 1
        elif exit_key in all_keys:
            core.quit()


# Function that waits until timer goes below zero.
def wait_timer(timer, exit_key, clock=False, exit=False, refresh_rate=8, invert=False):
    global exp_exit
    global key_list
    refresh_timer.reset(0)

    # Wait until main timer is at zero
    while timer.getTime() > 0:
        # Draw all stimuli
        win_1.flip()
        refresh_timer.addTime(1 / refresh_rate)

        # Check keys
        keys = event.getKeys(timeStamped=clock)
        if len(keys) > 0:
            key_list += keys
            if type(keys[0]) is list:
                keys = [key[0] for key in keys]
            if exit_key in keys:
                if exit is True:
                    core.quit()
                exp_exit = True

        # Wait until refresh timer
        while refresh_timer.getTime() > 0:
            pass

        # Invert checkboard so it flashes
        if invert is True and check_stim.autoDraw is True:
            check_stim.contrast *= -1


# Function to create monitor object
def create_monitor(mon_id, params, screen):
    mon = monitors.Monitor(
        mon_id,
        width=params["monitor"][mon_id]["width"],
        distance=params["monitor"][mon_id]["distance"],
    )
    mon_res = [screen.width, screen.height]
    mon.setSizePix(mon_res)

    return mon


# Load in json file containing parameters
with open("params.json", "r") as fid:
    params = json.load(fid)

# Setup dialog box to get study info
dlg = gui.Dlg(title="WSCT")
dlg.addField("Participant:")
dlg.addField("Experimenter:")
dlg.addField("Task:", choices=["WSCT", "VISMOTOR"])
dlg.addField("Mode:", choices=["Experiment", "Practice", "Post Test"])
dlg_data = dlg.show()

# Run dialog box
if dlg.OK:
    info_dic = {
        "Participant": dlg_data[0],
        "Experimenter": dlg_data[1],
        "Task": dlg_data[2],
        "Mode": dlg_data[3],
        "Date": data.getDateStr(),
    }
    info_dic["Task"] = info_dic["Task"].lower()
    info_dic["Mode"] = info_dic["Mode"].lower().replace(" ", "_")
else:
    core.quit()

# Recording logic
if (params["record"] is True and info_dic["Mode"] != "post_test") or (
    params["record_test"] is True and info_dic["Mode"] == "post_test"
):
    record = True
else:
    record = False
if record is True:
    mic = Microphone(device=0, streamBufferSecs=60, maxRecordingSize=175e3)

# Define data file names
out_root = (
    info_dic["Participant"]
    + "_"
    + info_dic["Date"]
    + "_"
    + info_dic["Task"]
    + "_"
    + info_dic["Mode"]
)
data_path = os.path.join("data/", out_root + "_data.csv")
iti_path = os.path.join("data/", out_root + "_iti.csv")

# Setup instructions
if info_dic["Task"] == "wsct":
    if info_dic["Mode"] == "experiment":
        instructions = ["The task will begin when you see a white crosshair."]
        final_msg = (
            "The task is now over. Please remain still while additional"
            + " scans are completed.\n\nThank you!"
        )
        img_idx = None
    elif info_dic["Mode"] == "practice":
        instructions = [
            "Welcome to the word-stem completion practice!\n\n"
            "You will be presented with a three letter word stem and "
            "asked to think of a word that completes it.\n\n"
            "Please do not speak the word out loud.",
            "For example, if you are shown HOU, you could think of "
            "'HOUSE', 'HOUR', or 'HOUND'.",
            "As you think of the word, please press the "
            f"{params['button_color']} button on the controller.\n\n"
            "Before we continue, could you press the "
            f"{params['button_color']} button?",
            "If you cannot think of an appropriate word, simply wait "
            "for the next one.\n\nPractice will begin when you see "
            "a white crosshair.",
        ]
        final_msg = (
            "The practice session is over.\n\n" + "Do you need additional practice?"
        )
        img_idx = 2
    else:
        instructions = [
            "Welcome to the word-stem completion post-test.\n\n"
            "You will be shown a series of word stems and asked to "
            "speak out loud a word that completes each stem.\n\n"
            "Please press space when you are ready to start"
        ]
        final_msg = "The post-test session is complete.\n\n" + "Thank you!"
        img_idx = None
else:
    if info_dic["Mode"] == "experiment":
        instructions = ["The task will begin when you see a white crosshair."]
        final_msg = (
            "The task is now over. Please remain still while additional"
            + " scans are completed.\n\nThank you!"
        )
        img_idx = None
    elif info_dic["Mode"] == "practice":
        instructions = [
            "Welcome to the task practice session!\n\nYou "
            "will be presented with a flashing circular "
            "checkerboard.",
            "When you see the checkerboard please press the "
            f"{params['button_color']} button on the "
            "controller.\n\nBefore we continue, could you press "
            f"the {params['button_color']} button?",
            "Practice will begin when you see a white crosshair.",
        ]
        final_msg = (
            "The practice session is over.\n\n" + "Do you need additional practice?"
        )
        img_idx = 1
    else:
        print("Post test is not an option for visual motor task")
        sys.exit()

# Get monitor information
display = pyglet.canvas.get_display()
screens = display.get_screens()
n_screen = len(screens)

# Create monitor and window for task
if n_screen > 1:
    task_scr_id = params["monitor"]["task"]["id"]
else:
    task_scr_id = 0
task_scr = screens[task_scr_id]
task_mon = create_monitor("task", params, task_scr)
win_1 = visual.Window(
    fullscr=params["monitor"]["task"]["full_screen"],
    color=(-1, -1, -1),
    monitor=task_mon,
    size=task_mon.getSizePix(),
    allowGUI=False,
    pos=[task_scr.x, task_scr.y],
)

# Get number of trials/scans
task_params = params["task"][info_dic["Task"]]
n_trial_scan = task_params["trials_per_scan"][info_dic["Mode"]]
n_trial = sum(n_trial_scan)
n_scan = len(n_trial_scan)

# Create file for data logging
data_file = open(data_path, "w")
data_file.write("# Participant : " + info_dic["Participant"] + "\n")
data_file.write("# Experimenter : " + info_dic["Experimenter"] + "\n")
data_file.write("# Task : " + info_dic["Task"] + "\n")
data_file.write("# Mode : " + info_dic["Mode"] + "\n")
data_file.write("# Date : " + info_dic["Date"] + "\n")
if info_dic["Task"] == "wsct":
    data_file.write("Scan,Scan.Start,Trial,Word,Onset,End,Key.List,Key.Bool\n")
else:
    data_file.write("Scan,Scan.Start,Trial,Onset,End,Key.List,Key.Bool\n")
data_file.close()

# Fixation stimulus
fix_stim = visual.TextStim(
    win=win_1,
    ori=0,
    text="+",
    font="Arial",
    pos=[-0.01, 0.1425],
    color="white",
    depth=-5.0,
    colorSpace="rgb",
    opacity=1,
    units=params["units"],
    height=params["font_size"]["fix"],
)
if info_dic["Mode"] == "post_test" or info_dic["Mode"] == "practice":
    fix_time = task_params["times"]["test_fix"]
else:
    fix_time = task_params["times"]["fix"]

# Task specific prep
if info_dic["Task"] == "wsct":
    # Load in list and remove new lines
    stem_path = task_params["lists"][info_dic["Mode"]]
    with open(stem_path) as fid:
        stem_list = fid.readlines()
    stem_list = [stem.strip() for stem in stem_list]

    # Shuffle list if neccessary
    if params["task"]["wsct"]["shuffle_stems"] is True:
        random.shuffle(stem_list)

    # Create text stimulus for wordstem
    stem_stim = visual.TextStim(
        win_1,
        pos=(0, 0),
        color="white",
        units=params["units"],
        text="Initial Text",
        height=params["font_size"]["stem"],
        wrapWidth=params["wrap_width"],
    )
    task_stim = [stem_stim]
    task_invert = False

else:
    # Create checkerboard stimulus
    check_params = params["task"]["vismotor"]["check"]
    check_stim = visual.RadialStim(
        win_1,
        pos=[0, 0],
        tex="sqrXsqr",
        ori=0,
        interpolate=True,
        color=1,
        units=params["units"],
        radialCycles=check_params["rad_cyc"],
        angularCycles=check_params["ang_cyc"],
        angularRes=check_params["ang_res"],
        texRes=check_params["tex_res"],
        size=check_params["size"],
    )

    # Remove center portion of checkerboard stimulus
    center_stim = visual.Polygon(
        win=win_1,
        edges=600,
        size=[2, 2],
        ori=0,
        pos=[0, 0],
        lineWidth=0,
        lineColor=[1, 1, 1],
        lineColorSpace="rgb",
        fillColor="black",
        fillColorSpace="rgb",
        opacity=1,
        depth=-4.0,
        interpolate=True,
        units=params["units"],
    )
    task_stim = [check_stim, center_stim, fix_stim]
    task_text = None
    task_invert = True

# Common text stimului
count_text = visual.TextStim(
    win_1,
    pos=(-8, -5),
    color="white",
    text="",
    units=params["units"],
    height=params["font_size"]["default"],
    wrapWidth=params["wrap_width"],
)
inst_text = visual.TextStim(
    win_1,
    pos=(0, 0),
    color="white",
    text="Initial Text",
    height=params["font_size"]["default"],
    wrapWidth=params["wrap_width"],
    units=params["units"],
)

# Get and save iti arrays
if task_params["times"]["iti"] == "variable":
    iti = np.zeros(n_trial)
    start_idx = 0
    for n in n_trial_scan:
        scan_iti, _ = poisson_iti(
            n,
            task_params["times"]["min"],
            task_params["times"]["mean"],
            task_params["times"]["max"],
        )
        iti[start_idx : start_idx + n] = scan_iti
        start_idx += n
else:
    iti = np.repeat(task_params["times"]["iti"], n_trial)
np.savetxt(iti_path, iti)

# Create image object for instructions
button_img = visual.ImageStim(
    win_1,
    image="button_box.png",
    pos=(0, -0.6),
    ori=-90,
    interpolate=True,
    size=[0.4, task_scr.width / task_scr.height * 0.4],
)

# Make circle stimulus to outline correct button
if params["button_color"] == "red":
    circle_pos = (0.0975, -0.605)
elif params["button_color"] == "green":
    circle_pos = (0.03, -0.605)
elif params["button_color"] == "yellow":
    circle_pos = (-0.0375, -0.605)
elif params["button_color"] == "blue":
    circle_pos = (-0.105, -0.605)
else:
    raise ValueError("Unknown button color: " + _)
circle_stim = visual.Circle(
    win_1,
    radius=0.03,
    pos=circle_pos,
    lineColor="white",
    fillColor=None,
    size=[1, task_scr.width / task_scr.height],
    lineWidth=6,
)

# Setup second screen if necessary
if n_screen == 2:
    # Create monitor and window for object
    con_scr = screens[params["monitor"]["con"]["id"]]
    con_mon = create_monitor("con", params, con_scr)
    win_2 = visual.Window(
        fullscr=params["monitor"]["con"]["full_screen"],
        color=(-1, -1, -1),
        monitor=con_mon,
        size=con_mon.getSizePix(),
        screen=params["monitor"]["con"]["id"],
    )

    # Stimuli for second monitor
    start_text = visual.TextStim(
        win_2,
        pos=(0, 0),
        color="Blue",
        text="Start Scan",
        units=params["units"],
        height=params["font_size"]["default"],
        wrapWidth=params["wrap_width"],
    )
    inst_2_text = visual.TextStim(
        win_2,
        pos=(0, 0),
        color="White",
        text="",
        units=params["units"],
        wrapWidth=params["wrap_width"],
        height=params["font_size"]["default"],
    )
    cont_text = visual.TextStim(
        win_2,
        pos=(0, -4.5),
        color="Blue",
        text="Press space to continue",
        units=params["units"],
        height=params["font_size"]["default"],
        wrapWidth=params["wrap_width"],
    )
    update_text = visual.TextStim(
        win_2,
        pos=(0, 0),
        color="Blue",
        text="",
        units=params["units"],
        height=params["font_size"]["update"],
        wrapWidth=params["wrap_width"],
    )

# Setup global clocks
timer = core.CountdownTimer()
refresh_timer = core.CountdownTimer()
clock = core.Clock()

# Show instructions
show_2 = n_screen == 2
for idx, instruct in enumerate(instructions):
    stim_list = None
    wait_key = "space"
    if info_dic["Mode"] == "practice" and idx == img_idx:
        stim_list = [button_img, circle_stim]
        wait_key = params["keys"]["button"]
    show_instruct(instruct, screen_2=show_2, extra=stim_list, wait_key=wait_key)
win_1.flip()

# Prep for loop
data_list = []
trial_idx = 0
scan_start = 0
n_resp_total = 0
key_list = []

# Debug
if params["debug"] is True:
    count_text.autoDraw = True

# Loop through scans
exp_exit = False
for scan in range(n_scan):
    # Tell control room to start scan
    n_resp_scan = 0

    # Add text to second screen
    if n_screen == 2:
        if info_dic["Mode"] != "experiment":
            start_text.setText("Press space to start practice")
        start_text.draw()
        win_2.flip()

    # Wait for trigger before doing anything
    if info_dic["Mode"] != "post_test":
        if info_dic["Mode"] != "experiment":
            trig_key = "space"
        else:
            trig_key = params["keys"]["trig"]
        wait_trig(1, trig_key, params["keys"]["exit"])

    # Reset time
    timer.reset(0)
    if scan == 0:
        clock.reset()
    scan_start_time = clock.getTime()

    # Show cursor
    if fix_time > 0 and task_params["trials_per_scan"]["bold_bool"][scan] is True:
        show_stim([fix_stim], fix_time)
        if n_screen == 2:
            win_2.flip()
        wait_timer(timer, params["keys"]["exit"], exit=True)
        fix_stim.autoDraw = False

    # Loop through number of trials per scan
    for trial in range(n_trial_scan[scan]):
        key_list = []

        # Show first trial
        if trial == 0:
            start_time = clock.getTime()
            if info_dic["Task"] == "wsct":
                task_text = stem_list[trial_idx]
            show_stim(
                task_stim,
                task_params["times"]["ti"],
                text=task_text,
                show_count=params["debug"],
            )

            # Update progress screen if necessary
            if n_screen == 2:
                update_prog(0)

            # Start recording if necessary
            if record is True:
                mic.start()

        # Wait for trial period to end
        wait_timer(timer, params["keys"]["exit"], clock=clock, invert=task_invert)
        for stim in task_stim:
            stim.autoDraw = False
        fix_stim.autoDraw = False
        end_time = clock.getTime()

        # Show fixation
        show_stim([fix_stim], iti[trial_idx], show_count=params["debug"])

        # Wait for iti to end
        wait_timer(timer, params["keys"]["exit"], clock=clock)
        fix_stim.autoDraw = False
        trial_idx += 1

        # Get user input
        key_list = [key for key in key_list if key[0] != params["keys"]["trig"]]
        resp_keys = [key[0] for key in key_list]
        key_bool = [key[0] == params["keys"]["button"] for key in key_list]
        skip = all(key in resp_keys for key in list("skip"))
        pause = all(key in resp_keys for key in list("pause"))

        # Pause if necessary
        if pause is True:
            pause_start = clock.getTime()

            # Let exerimenter know we are in pause mode
            if n_screen == 2:
                pause_str = "Task is paused. Press space to continue."
                update_text.setText(pause_str)
                update_text.draw()
                win_2.flip()

            # Wait for space bar to continue
            wait_trig(1, "space", params["keys"]["exit"])

            # Removed time in apuse from timer
            pause_end = clock.getTime()
            timer.addTime(pause_end - pause_start)
        next_time = clock.getTime()

        # Start next trial
        if trial != n_trial_scan[scan] - 1 and skip is False:
            if info_dic["Task"] == "wsct":
                task_text = stem_list[trial_idx]
            show_stim(
                task_stim,
                task_params["times"]["ti"],
                text=task_text,
                show_count=params["debug"],
            )
            if n_screen == 2:
                resp_bool = any(key_bool)
                n_resp_scan += resp_bool
                n_resp_total += resp_bool
                update_prog(trial + 1)
        else:
            show_stim([fix_stim], 0, show_count=params["debug"])

        # Save data from previous trial
        if info_dic["Task"] == "wsct":
            data_list.append(
                [
                    scan,
                    round(scan_start_time, 6),
                    trial_idx - 1,
                    stem_list[trial_idx - 1],
                    round(start_time, 6),
                    round(end_time, 6),
                    key_list,
                    key_bool,
                ]
            )
        else:
            data_list.append(
                [
                    scan,
                    round(scan_start_time, 6),
                    trial_idx - 1,
                    round(start_time, 6),
                    round(end_time, 6),
                    key_list,
                    key_bool,
                ]
            )
        if pause is False:
            start_time = next_time
        if record is True:
            mic.poll()

        # Exit scan block if necessary
        if skip is True:
            break

        # Quit if necessary
        if exp_exit is True:
            break

    # Save audio file if necessary
    if record is True:
        mic.stop()
        audio_clip = mic.getRecording()
        audio_path = os.path.join("audio/", out_root + "_" + str(scan) + ".wav")
        audio_clip.save(audio_path)
        mic.clear()

    # Update data file
    with open(data_path, "a") as data_file:
        for i in range(scan_start, trial_idx):
            out_str = ",".join([str(item) for item in data_list[i]]) + "\n"
            data_file.write(out_str)

    # Show cursor
    if fix_time > 0 and task_params["trials_per_scan"]["bold_bool"][scan] is True:
        show_stim([fix_stim], fix_time)
        wait_timer(timer, params["keys"]["exit"], exit=True)

    # Update indicies for saving data
    scan_start = trial_idx

    # Exit if necessary
    if exp_exit is True:
        core.quit()

# Show final message
fix_stim.autoDraw = False
show_instruct(final_msg, screen_2=show_2)

# All done!
core.quit()
