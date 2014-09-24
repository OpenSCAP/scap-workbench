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

    mTranslator(),
    mMainWindow(new MainWindow())
{
    setOrganizationName("scap-workbench upstream");
    setOrganizationDomain("http://fedorahosted.org/scap-workbench");

    setApplicationName("scap-workbench");
    setApplicationVersion(SCAP_WORKBENCH_VERSION);

    mTranslator.load(QLocale(), "scap-workbench", "", getShareTranslationDirectory().absolutePath());
    installTranslator(&mTranslator);

    const QIcon& icon = getApplicationIcon();
    setWindowIcon(icon);
    mMainWindow->setWindowIcon(icon);

    QObject::connect(
        this, SIGNAL(lastWindowClosed()),
        this, SLOT(quit())
    );

    processCLI(arguments());

    // Only open default content if no command line arguments were given.
    // The first argument is the application name, it doesn't count.
    if (!mMainWindow->fileOpened() && arguments().length() < 2)
        openDefaultContent();

    mMainWindow->show();

    if (!mMainWindow->fileOpened())
        browseForContent();
}

Application::~Application()
{
    delete mMainWindow;
}

void Application::processCLI(const QStringList& args)
{
    if (args.length() > 1)
    {
        // The last argument will hold the path to file that user wants to open.
        // For now we just ignore all other options.

        mMainWindow->openFile(args.last());
    }
}

void Application::openDefaultContent()
{
    const QString defaultContent = SCAP_WORKBENCH_DEFAULT_CONTENT;

    // We silently ignore badly configured default content paths and avoid
    // opening them.
    if (!defaultContent.isEmpty() && QFileInfo(defaultContent).isFile())
        mMainWindow->openFile(defaultContent);
}

void Application::browseForContent()
{
    mMainWindow->openFileDialogAsync();
}
