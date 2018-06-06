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

#ifndef SCAP_WORKBENCH_OSCAP_SCANNER_LOCAL_H_
#define SCAP_WORKBENCH_OSCAP_SCANNER_LOCAL_H_

#include <QTemporaryFile>

#include "ForwardDecls.h"
#include "OscapScannerBase.h"


class OscapScannerLocal : public OscapScannerBase
{
    Q_OBJECT

    public:
        OscapScannerLocal();
        virtual ~OscapScannerLocal();

        virtual QStringList getCommandLineArgs() const;
        virtual void evaluate();
        /**
         * @brief Return the executable name to execute and adjusts args if neccessary
         * (e.g. the executable is a launcher and s.a. 'nice' and the oscap itself
         * has to be added as an argument to it, i.e. prepended to args)
         *
         * @returns false when there is nothing to be read, true otherwise
         * @see readStdOut
         */
        static QString getOscapProgramAndAdaptArgs(QStringList& args);

    private:
        static QString getPkexecOscapPath();
        void fillInCapabilities();

        void evaluateWithOfflineRemediation();
        void evaluateWithOtherSettings();
        static void setFilenameToTempFile(QTemporaryFile& file);
};

#endif
