#!/usr/bin/zsh

. ~/.zshrc

csc --define LINUX --out FFFocusTracker --source FFFocusTracker.cs FFCommon.cs
csc --define LINUX --out FFLinkRouter --source FFLinkRouter.cs FFCommon.cs

sudo mv FFFocusTracker $BINARIES
sudo mv FFLinkRouter $BINARIES

systemctl --user restart fffocus-tracker.service
