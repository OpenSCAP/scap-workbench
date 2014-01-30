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

#include <QFileInfo>

Application::Application(int& argc, char** argv):
    QApplication(argc, argv),
    mMainWindow(new MainWindow())
{
    setApplicationName("scap-workbench");
    setApplicationVersion(SCAP_WORKBENCH_VERSION);

    QString iconPath = qgetenv("SCAP_WORKBENCH_ICON");
    QIcon icon = QIcon(iconPath.isEmpty() ? SCAP_WORKBENCH_ICON : iconPath);

    setWindowIcon(icon);
    mMainWindow->setWindowIcon(icon);

    QObject::connect(
        this, SIGNAL(lastWindowClosed()),
        this, SLOT(quit())
    );

    QStringList args = arguments();
    if (args.length() > 1)
    {
        // The last argument will hold the path to file that user wants to open.
        // For now we just ignore all other options.

        mMainWindow->openFile(args.last());
    }
    else
    {
        // No arguments given, lets check if there is any default content to open.

        const QString defaultContent = SCAP_WORKBENCH_DEFAULT_CONTENT;

        // We silently ignore badly configured default content paths and avoid
        // opening them.
        if (!defaultContent.isEmpty() && QFileInfo(defaultContent).isFile())
            mMainWindow->openFile(defaultContent);
    }

    // When all else fails, we just show the open file dialog.
    if (!mMainWindow->fileOpened())
        mMainWindow->openFileDialogAsync();
}

Application::~Application()
{
    delete mMainWindow;
}
