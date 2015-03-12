/*
 * Copyright 2013 Red Hat Inc., Durham, North Carolina.
 * All Rights Reserved.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *      Martin Preisler <mpreisle@redhat.com>
 */

#include "Application.h"
#include "MainWindow.h"
#include "Utils.h"

#include <QFileInfo>
#include <QTranslator>

Application::Application(int& argc, char** argv):
    QApplication(argc, argv),

    mSkipValid(false),
    mTranslator(),
    mMainWindow(0)
{
    setOrganizationName("SCAP Workbench upstream");
    setOrganizationDomain("http://fedorahosted.org/scap-workbench");

    setApplicationName("SCAP Workbench");
    setApplicationVersion(SCAP_WORKBENCH_VERSION);

    mMainWindow = new MainWindow();

#if (QT_VERSION >= QT_VERSION_CHECK(4, 8, 0))
    mTranslator.load(QLocale(), "scap-workbench", "", getShareTranslationDirectory().absolutePath());
    installTranslator(&mTranslator);
#endif

    const QIcon& icon = getApplicationIcon();
    setWindowIcon(icon);
    mMainWindow->setWindowIcon(icon);

    QObject::connect(
        this, SIGNAL(lastWindowClosed()),
        this, SLOT(quit())
    );
    mMainWindow->show();

    QStringList args = arguments();
    processCLI(args);

    mMainWindow->setSkipValid(mSkipValid);

    // Only open default content if no command line arguments were given.
    // The first argument is the application name, it doesn't count.
    if (!mMainWindow->fileOpened() && args.length() < 2)
        openSSG();

    if (!mMainWindow->fileOpened())
        browseForContent();
}

Application::~Application()
{
    delete mMainWindow;
}

void Application::processCLI(QStringList& args)
{
    if (args.contains("--skip-valid"))
    {
        mSkipValid = true;
        args.removeAll("--skip-valid");
    }

    if (args.length() > 1)
    {
        // The last argument will hold the path to file that user wants to open.
        // For now we just ignore all other options.

        mMainWindow->openFile(args.last());
    }
}

void Application::openSSG()
{
    mMainWindow->openSSGDialog(QObject::tr("Open other SCAP Content"));
}

void Application::browseForContent()
{
    mMainWindow->openFileDialogAsync();
}
