EMAV - Experimental Modal Analysis Viewer (v0.2.1)

Description

EMAV (Experimental Modal Analysis Viewer) is a bespoke software tool developed in Python, designed for the visualization and comparative analysis of experimental modal analysis data. Its primary function is to allow engineers and technicians to visually compare reconstructed Frequency Response Functions (FRFs) against a library of raw measurement data (e.g., from Siemens Testlab) to find the best match.

The tool supports both multi-record .unv and .mat files from testing software and single-record, linear-amplitude .unv files representing reconstructed signals.

Key Features

Dual Data Source Loading: Load multi-record Testlab files (.unv, .mat) and single-record reconstructed FRF files (.unv).

Interactive Tree View: Easily navigate through different records within a loaded Testlab file.

Dual-Plot Comparison:

A dedicated plot for the reconstructed signal (linear scale).

A dedicated plot for the selected Testlab record.

Dynamic Scale Control:

Toggle the Testlab FRF amplitude plot between logarithmic (with fixed 10^-3 to 10^2 limits) and linear scales for direct comparison.

Manually set and reset X/Y axis limits on the reconstructed plot to "stretch" and "zoom" for detailed analysis.

Smart Data Handling: Automatically distinguishes between complex-valued FRF data (plotting magnitude and phase) and real-valued data like PSD or Coherence (plotting a single trace).

Data Export: Save a selected complex FRF from a Testlab file into a new, simplified .unv file containing only frequency and linear amplitude, matching the format of the reconstructed signals.

Current Status & Known Issues (v0.2.1)

The application is currently in a debugging phase. While the Testlab file loading and plotting functionalities are stable, there is a known issue preventing the loading of reconstructed .unv files.

Problem: The pyuff library, used for parsing .unv files, cannot handle an in-memory stream of data. The current workaround—which pre-processes the file to remove an incompatible header (Dataset 151)—results in a TypeError because it passes an in-memory object instead of a required file path.

Next Step: The immediate priority is to modify the loading mechanism to write the cleaned file content to a temporary physical file on disk before passing its path to the pyuff library. This will be addressed in the next version.

Installation and Setup

EMAV is designed to be run from a local folder without a complex installation process.

Prerequisites:

Python 3.12 or newer.

Instructions:

Place the following three files into a single folder:

emav_app.py

requirements.txt

RUN_EMAV.bat

Add your .unv and .mat data files to the same folder.

Double-click RUN_EMAV.bat.

This batch file will automatically perform the following steps:

Create a Python virtual environment named emavenv.

Activate the virtual environment.

Install all necessary dependencies from requirements.txt.

Launch the EMAV application.

Usage Guide

Load Testlab Data: Click the "Load Testlab File" button to open a .unv or .mat file. The records will appear in the tree view on the left.

Load Reconstructed FRF: Click the "Load Reconstructed FRF" button to open your reference .unv file. It will be displayed in the top plot.

Compare: Select a record from the tree view. Its data will be plotted in the bottom graph.

Analyze:

Use the "[✓] Log Scale" checkbox to toggle the bottom plot's Y-axis between logarithmic and linear scales.

Use the X/Y Min/Max input fields and the "Apply Scale" button to zoom in on the top plot.

Save: Once you have found a matching record in the Testlab data, ensure it is selected in the tree, and click the "Save Selected Testlab Record" button to export it as a linear-amplitude .unv file.

Dependencies

tkinter (Standard with Python)

scipy

numpy

matplotlib

pyuff
