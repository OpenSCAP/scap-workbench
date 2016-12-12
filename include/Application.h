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

#include "ForwardDecls.h"
#include <QApplication>
#include <QTranslator>

/**
 * @brief Central application
 *
 * Constructs the MainWindow.
 * Technically, this class is a singleton because of the qApp global pointer
 * and the QCoreApplication::instance() static method.
 *
 * This class is virtual solely because of the qApp() macro and the singleton
 * nature of QApplication.
 */
class Application : public QApplication
{
    public:
        /**
         * Make *sure* argc will be valid during lifetime of this class, you are
         * passing a reference! Qt can alter argc when it parses the command line.
         * If argc is deleted by then this will cause an invalid write!
         */
        Application(int& argc, char** argv);
        virtual ~Application();

    private:
        /**
         * @brief Processes command line arguments and acts accordingly
         */
        void processCLI(QStringList& args);

        /**
         * @brief Opens the SSG integration dialog to let user open SSG
         */
        void openSSG();

        /**
         * @brief Opens a file dialog, allowing user to open any content
         */
        void browseForContent();

        /**
         * @brief Prints version of SCAP Workbench
         */
        void printVersion();

        /**
         * @brief Prints help of SCAP Workbench
         */
        void printHelp();

        /// Whether the application should quit
        bool mShouldQuit;

        bool mSkipValid;
        /// Needed for QObject::tr(..) to work properly, loaded on app startup
        QTranslator mTranslator;
        MainWindow* mMainWindow;
};
