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

#ifndef SCAP_WORKBENCH_SCANNING_SESSION_H_
#define SCAP_WORKBENCH_SCANNING_SESSION_H_

#include "ForwardDecls.h"
#include <QObject>

extern "C"
{
#include <xccdf_benchmark.h>
}

/**
 */
class ScanningSession : public QObject
{
    Q_OBJECT

    public:
        ScanningSession(DiagnosticsDialog* diagnosticsDialog, QObject* parent = 0);
        ~ScanningSession();

    public slots:
        /**
         * @brief Opens a specific file
         *
         * Passed file may be an XCCDF file (any openscap supported version)
         * or source datastream (SDS) file (any openscap supported version)
         */
        void openFile(const QString& path);

        /**
         * @brief Closes currently opened file (if any)
         */
        void closeFile();

        bool isSDS() const;

        void setDatastreamID(const QString& datastreamID, bool skipReload = false);
        void setComponentID(const QString& componentID, bool skipReload = false);

        void resetTailoring();
        void setTailoringFile(const QString& tailoringFile);
        void setTailoringComponentID(const QString& componentID);

        bool setProfileID(const QString& profileID);

        /**
         * @brief Reloads the session, datastream split is potentially done again
         *
         * The main purpose of this method is to allow to reload the session when
         * parameters that affect "loading" of the session change. These parameters
         * are mainly datastream ID and component ID.
         */
        void reloadSession();

        struct xccdf_session* getXCCDFSession() const;

        bool fileOpened() const;
        bool profileSelected() const;

        /**
         * @brief Creates a new profile, makes it inherit current profile
         *
         * @param shadowed if true the new profile will have the same ID
         * @return created profile (can be passed to TailoringWindow for further tailoring)
         */
        struct xccdf_profile* tailorCurrentProfile(bool shadowed = false);

    private:
        /// This is our central point of interaction with openscap
        struct xccdf_session* mSession;

        /// Qt Dialog that displays messages (errors, warnings, infos)
        /// Gets shown whenever a warning or error is emitted
        DiagnosticsDialog* mDiagnosticsDialog;
};

#endif
