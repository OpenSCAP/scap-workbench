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

#include <iostream>

Application::Application(int& argc, char** argv):
    QApplication(argc, argv),

    mShouldQuit(false),
    mSkipValid(false),
    mTranslator(),
    mMainWindow(0)
{
    setOrganizationName("SCAP Workbench upstream");
    setOrganizationDomain("https://www.open-scap.org/tools/scap-workbench");

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

    if (mShouldQuit)
    {
        mMainWindow->closeMainWindowAsync();
        return;
    }

    mMainWindow->setSkipValid(mSkipValid);

    // Only open default content if no file to open was given.
    if (!mMainWindow->fileOpened())
        openSSG();

}

Application::~Application()
{
    delete mMainWindow;
}

void Application::processCLI(QStringList& args)
{
    if (args.contains("-V") || args.contains("--version"))
    {
        printVersion();
        mShouldQuit = true;
        return;
    }

    if (args.contains("-h") || args.contains("--help"))
    {
        printHelp();
        mShouldQuit = true;
        return;
    }

    if (args.contains("--skip-valid"))
    {
        mSkipValid = true;
        args.removeAll("--skip-valid");
    }

    if (args.length() > 1)
    {
        QStringList unknownOptions = args.filter(QRegExp("^-{1,2}.*"));

        if (!unknownOptions.isEmpty())
        {
            QString unknownOption = QString("Unknown option '%1'\n").arg(unknownOptions.first());
            std::cout << unknownOption.toUtf8().constData();
            printHelp();
            mShouldQuit = true;
            return;
        }

        // For now we just ignore all other arguments.
        mMainWindow->openFile(args.last());
    }
}

void Application::openSSG()
{
    mMainWindow->openSSGDialog(QObject::tr("Close SCAP Workbench"));
}

void Application::browseForContent()
{
    mMainWindow->openFileDialogAsync();
}

void Application::printVersion()
{
    const QString versionInfo = QString("SCAP Workbench %1\n").arg(SCAP_WORKBENCH_VERSION);
    std::cout << versionInfo.toUtf8().constData();
}

void Application::printHelp()
{
    const QString help = QString(
            "Usage: ./scap-workbench [options] [file]\n"
            "\nOptions:\n"
            "   -h, --help\r\t\t\t\t Displays this help.\n"
            "   -V, --version\r\t\t\t\t Displays version information.\n"
            "   --skip-valid\r\t\t\t\t Skips OpenSCAP validation.\n"
            "\nArguments:\n"
            "   file\r\t\t\t\t A file to load, can be an XCCDF or SDS file.\n");

    std::cout << help.toUtf8().constData();
}
