# code taken and adapted from https://gist.github.com/MadeBaruna/1d75c1d37d19eca71591ec8a31178235
$logLocation = "%userprofile%\AppData\LocalLow\miHoYo\Genshin Impact\output_log.txt";

$path = [System.Environment]::ExpandEnvironmentVariables($logLocation);
if (-Not [System.IO.File]::Exists($path)) {
    Write-Host "Cannot find the log file! Make sure to open the wish history first!" -ForegroundColor Red

    if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {  
        Write-Host "Do you want to try to run the script as Administrator? Press [ENTER] to continue, or any key to cancel."
        $keyInput = [Console]::ReadKey($true).Key
        if ($keyInput -ne "13") {
            return
        }
        $arguments = "& '" +$myinvocation.mycommand.definition + "'"
        Start-Process powershell -Verb runAs -ArgumentList "-noexit", $arguments
        break
    }

    return
}

$logs = Get-Content -Path $path
$match = $logs -match "^OnGetWebViewPageFinish.*log$"

if (-Not $match) {
    Write-Host "Cannot find the wish history url! Make sure to open the wish history first!" -ForegroundColor Red
    return
}
[string] $wishHistoryUrl = $match[$match.Length - 1]  -replace 'OnGetWebViewPageFinish:', ''
Write-Host $wishHistoryUrl
Set-Clipboard -Value $wishHistoryUrl
Write-Host "Link copied to clipboard, now paste it into the dialogue box from the bot after clicking the button." -ForegroundColor Green