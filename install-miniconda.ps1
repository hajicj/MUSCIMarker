# Script to set up Miniconda with a test environment

# This script has been heavily adapted from a script by Olivier Grisel and Kyle
# Kastner licensed under a BSD 3-clause license, and subsequently modified by
# Stuart Mumford before being adapted to its current form in ci-helper.

# We use the following function to exit the script after any failing command
function checkLastExitCode {
  if ($lastExitCode) {
    echo "ERROR: the last command returned the following exit code: $lastExitCode"
    Exit $lastExitCode
  }
}

$QUIET = "-q"

if ($env:DEBUG) {
    if($env:DEBUG -match "True") {

        # Show all commands
        Set-PSDebug -Trace 1

        # Print out environment variables
        Get-ChildItem Env:

        # Disable Quiet mode
        $QUIET = ""

    }
}

$MINICONDA_URL = "https://repo.continuum.io/miniconda/"

$env:USED_NUMPY_VERSION = "1.13"
$env:PYTHON_VERSION = 2.7

if (! $env:PIP_FALLBACK) {
   $env:PIP_FALLBACK = "True"
}

function DownloadMiniconda ($version, $platform_suffix) {
    $webclient = New-Object System.Net.WebClient
    $filename = "Miniconda3-" + $version + "-Windows-" + $platform_suffix + ".exe"

    $url = $MINICONDA_URL + $filename
    $basedir = $pwd.Path + "\"

    $filepath = $basedir + $filename
    if (Test-Path $filename) {
        Write-Host "Reusing" $filepath
        return $filepath
    }

    # Download and retry up to 3 times in case of network transient errors.
    Write-Host "Downloading" $filename "from" $url
    $retry_attempts = 2
    for($i=0; $i -lt $retry_attempts; $i++){
        try {
            $webclient.DownloadFile($url, $filepath)
            break
        }
        Catch [Exception]{
            Start-Sleep 1
        }
   }
   if (Test-Path $filepath) {
       Write-Host "File saved at" $filepath
   } else {
       # Retry once to get the error message if any at the last try
       $webclient.DownloadFile($url, $filepath)
   }
   return $filepath
}

function InstallMiniconda ($miniconda_version, $architecture, $python_home) {
    Write-Host "Installing miniconda" $miniconda_version "for" $architecture "bit architecture to" $python_home
    if (Test-Path $python_home) {
        Write-Host $python_home "already exists, skipping."
        return $false
    }
    if ($architecture -eq "x86") {
        $platform_suffix = "x86"
    } else {
        $platform_suffix = "x86_64"
    }
    $filepath = DownloadMiniconda $miniconda_version $platform_suffix
    Write-Host "Installing" $filepath "to" $python_home
    $args = "/S /AddToPath=1 /RegisterPython=1 /D=" + $python_home
    Write-Host $filepath $args
    Start-Process -FilePath $filepath -ArgumentList $args -Wait -Passthru
    #Start-Sleep -s 15
    if (Test-Path $python_home) {
        Write-Host "Miniconda $miniconda_version ($architecture) installation complete"
    } else {
        Write-Host "Failed to install Python in $python_home"
        Exit 1
    }
}

# Install miniconda, if no version is given use the latest
if (! $env:MINICONDA_VERSION) {
   $env:MINICONDA_VERSION="latest"
}

# Install miniconda for Windows x64, if no environment is given
if (! $env:PLATFORM) {
   $env:PLATFORM="x86_64"
}

# Install no python path is specified 
if (! $env:PYTHON) {
   $env:PYTHON= $pwd.Path + "\" + "Python"
}

InstallMiniconda $env:MINICONDA_VERSION $env:PLATFORM $env:PYTHON
checkLastExitCode

# Set environment variables
$env:PATH = "${env:PYTHON};${env:PYTHON}\Scripts;" + $env:PATH

# Conda config

conda config --set always_yes true
checkLastExitCode

conda config --add channels anaconda
checkLastExitCode

if ($env:CONDA_CHANNELS) {
   $CONDA_CHANNELS=$env:CONDA_CHANNELS.split(" ")
   foreach ($CONDA_CHANNEL in $CONDA_CHANNELS) {
       conda config --add channels $CONDA_CHANNEL
       checkLastExitCode
   }
   Remove-Variable CONDA_CHANNELS
   rm env:CONDA_CHANNELS
}

# Create a conda environment
conda create $QUIET -n test python=$env:PYTHON_VERSION
checkLastExitCode

activate test
checkLastExitCode

# Set environment variables for environment (activate test doesn't seem to do the trick)
$env:PATH = "${env:PYTHON}\envs\test;${env:PYTHON}\envs\test\Scripts;${env:PYTHON}\envs\test\Library\bin;" + $env:PATH

# Check that we have the expected version of Python
# python --version # Don't output, because it prints this thing to the std-error output
pip --version

conda install $QUIET -n test pytest pip numpy scipy matplotlib pytest h5py scikit-image
checkLastExitCode

python -m pip install --upgrade pip wheel setuptools
pip --version

pip install -r requirements.txt
pip install -r requirements_windows.txt
