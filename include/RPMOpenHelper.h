/*
 * Copyright 2014 Red Hat Inc., Durham, North Carolina.
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

#ifndef SCAP_WORKBENCH_RPM_OPEN_HELPER_H_
#define SCAP_WORKBENCH_RPM_OPEN_HELPER_H_

#include "ForwardDecls.h"
#include "TemporaryDir.h"
#include <QWidget>

/**
 * @brief Creates local temporary directory with contents of given scap-workbench RPM
 *
 * The reason this class exists is because openscap API is quite limited when
 * it comes to input. It will only take file paths.
 *
 * Intended usage:
 * @code{.cpp}
 * // Assumes openscap 1.0 API.
 * struct xccdf_session* sess = 0;
 * {
 *     RPMOpenHelper helper("some-packaged-scap-content-1.rpm");
 *     // helper automatically creates a temporary directory, extracts everything
 *     // to it and stores the paths that can later be used
 *
 *     sess = xccdf_session_new(helper.getInputPath());
 *
 *     if (helper.hasTailoring())
 *         xccdf_session_set_user_tailoring_file(sess, helper.getTailoringPath());
 *
 *     xccdf_session_load(sess);
 * }
 *
 * // At this point helper goes out of scope and the temporary directory is
 * // recursively deleted. However the session has been loaded and can still be used!
 * @endcode
 */
class RPMOpenHelper
{
    public:
        explicit RPMOpenHelper(const QString& path);
        ~RPMOpenHelper();

        const QString& getInputPath() const;
        bool hasTailoring() const;
        const QString& getTailoringPath() const;

    private:
        static QString getRPMExtractPath();

        TemporaryDir mTempDir;

        QString mInputPath;
        QString mTailoringPath;
};

#endif
