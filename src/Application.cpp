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
#include <QCommandLineParser>

#include <iostream>

Application::Application(int& argc, char** argv):
    QApplication(argc, argv),
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

    QStringList args = arguments();
    processCLI(args);

    // Showing the window before processing command line arguments causes crashes occasionally
    mMainWindow->show();

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
    QCommandLineParser parser;

    parser.addHelpOption();
    parser.addVersionOption();

    QCommandLineOption skipValid("skip-valid", "Skips OpenSCAP validation.");
    parser.addOption(skipValid);

    QCommandLineOption tailoring("tailoring", "Opens the given tailoring file after "
                                              "the given XCCDF or SDS file is loaded.",
                                 "ssg-tailoring.xml");
    parser.addOption(tailoring);

    parser.addPositionalArgument("file", "A file to load; can be either an XCCDF or SDS file.", "[file]");
    parser.process(args);

    if (parser.isSet(skipValid))
    {
        mMainWindow->setSkipValid(true);
    }

    QStringList posArguments = parser.positionalArguments();
    if (posArguments.isEmpty())
    {
        if (parser.isSet(tailoring))
        {
            std::cout << "Tailoring file was provided via --tailoring, but no SCAP "
                      << "input was provided. Ignoring the tailoring file."
                      << std::endl;
        }
        return;
    }

    mMainWindow->openFile(posArguments.first());

    if (parser.isSet(tailoring))
        mMainWindow->openTailoringFile(parser.value(tailoring));

    // We ignore all other positional arguments suplied, if any
}

void Application::openSSG()
{
    mMainWindow->openSSGDialog(QObject::tr("Close SCAP Workbench"));
}

void Application::browseForContent()
{
    mMainWindow->openFileDialogAsync();
}
